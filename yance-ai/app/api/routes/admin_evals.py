from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import Principal, require_platform_admin
from app.core.config import settings
from app.core.db import get_db
from app.models.models import (
    EvalCase,
    EvalDataset,
    EvalDatasetVersion,
    EvalRun,
    Evaluation,
    EvaluationDimensionScore,
    EvaluationError,
    EvaluationEvidence,
)
from app.schemas.schemas import EvalRunRequest
from app.services.evaluations.contracts import EVAL_TYPES, EvalType
from app.services.evaluations.metrics import evaluation_overview
from app.services.evaluations.runner import execute_bundle, persist_executions

router = APIRouter(prefix="/admin/evals", tags=["admin", "evaluations"])


def _run_summary(run: EvalRun) -> dict:
    return {
        "id": str(run.id),
        "batch_id": str(run.batch_id),
        "eval_type": run.eval_type,
        "status": run.status,
        "target_key": run.target_key,
        "target_version": run.target_version,
        "scorer_version": run.scorer_version,
        "model": run.model,
        "requested_cases": run.requested_cases,
        "completed_cases": run.completed_cases,
        "passed_cases": run.passed_cases,
        "error_cases": run.error_cases,
        "total_latency_ms": run.total_latency_ms,
        "total_cost_usd": float(run.total_cost_usd or 0),
        "release_gate_passed": run.release_gate_passed,
        "created_at": run.created_at,
        "finished_at": run.finished_at,
    }


@router.get("/overview")
def get_evaluation_overview(
    eval_type: EvalType | None = None,
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    return evaluation_overview(db, eval_type)


@router.get("/runs")
def list_evaluation_runs(
    limit: int = 50,
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    safe_limit = min(max(limit, 1), 100)
    runs = db.scalars(select(EvalRun).order_by(EvalRun.created_at.desc()).limit(safe_limit)).all()
    return {"items": [_run_summary(run) for run in runs]}


@router.post("/runs", status_code=201)
def create_evaluation_runs(
    payload: EvalRunRequest,
    principal: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    selected: list[EvalType] = (
        list(EVAL_TYPES) if payload.eval_type == "all" else [payload.eval_type]
    )
    try:
        executions = execute_bundle(Path(settings.eval_dataset_root), selected)
        runs = persist_executions(
            db,
            executions,
            tenant_id=principal.tenant_id,
            user_id=principal.user.id,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "batch_id": str(runs[0].batch_id) if runs else None,
        "runs": [_run_summary(run) for run in runs],
        "release_gate_passed": bool(runs) and all(run.release_gate_passed for run in runs),
    }


@router.get("/runs/{run_id}")
def get_evaluation_run(
    run_id: UUID,
    _: Principal = Depends(require_platform_admin),
    db: Session = Depends(get_db),
) -> dict:
    row = db.execute(
        select(EvalRun, EvalDatasetVersion, EvalDataset)
        .join(EvalDatasetVersion, EvalDatasetVersion.id == EvalRun.dataset_version_id)
        .join(EvalDataset, EvalDataset.id == EvalDatasetVersion.dataset_id)
        .where(EvalRun.id == run_id)
    ).one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Evaluation run not found")
    run, version, dataset = row
    result_rows = db.execute(
        select(Evaluation, EvalCase)
        .join(EvalCase, EvalCase.id == Evaluation.eval_case_id)
        .where(Evaluation.eval_run_id == run.id)
        .order_by(EvalCase.case_id)
    ).all()
    evaluation_ids = [result.id for result, _ in result_rows]
    dimensions = db.scalars(
        select(EvaluationDimensionScore).where(
            EvaluationDimensionScore.evaluation_id.in_(evaluation_ids)
        )
    ).all()
    evidence = db.scalars(
        select(EvaluationEvidence).where(EvaluationEvidence.evaluation_id.in_(evaluation_ids))
    ).all()
    errors = db.scalars(
        select(EvaluationError).where(EvaluationError.eval_run_id == run.id)
    ).all()
    return {
        "run": _run_summary(run),
        "dataset": {
            "key": dataset.key,
            "name": dataset.name,
            "description": dataset.description,
            "version": version.version,
            "content_sha256": version.content_sha256,
            "review_status": version.review_status,
            "data_classification": dataset.data_classification,
            "case_count": version.case_count,
            "card": version.card_json,
        },
        "cases": [
            {
                "case_id": case.case_id,
                "question": case.question,
                "risk_tier": case.risk_tier,
                "tags": case.tags_json,
                "ground_truth": case.ground_truth_json,
                "model_answer": result.model_answer_json,
                "status": result.status,
                "overall_score": float(result.overall_score)
                if result.overall_score is not None
                else None,
                "passed": result.passed,
                "latency_ms": result.latency_ms,
                "cost_usd": float(result.cost_usd or 0),
                "error_types": result.error_types_json,
                "dimensions": [
                    {
                        "dimension": item.dimension,
                        "score": float(item.score) if item.score is not None else None,
                        "is_applicable": item.is_applicable,
                        "scorer": item.scorer,
                        "scorer_version": item.scorer_version,
                        "rationale": item.rationale,
                    }
                    for item in dimensions
                    if item.evaluation_id == result.id
                ],
                "evidence": [
                    {
                        "expectation": item.expectation,
                        "observed": item.observed,
                        "source_reference": item.source_reference,
                        "passed": item.passed,
                    }
                    for item in evidence
                    if item.evaluation_id == result.id
                ],
                "errors": [
                    {
                        "code": item.code,
                        "error_type": item.error_type,
                        "safe_message": item.safe_message,
                    }
                    for item in errors
                    if item.evaluation_id == result.id
                ],
            }
            for result, case in result_rows
        ],
    }
