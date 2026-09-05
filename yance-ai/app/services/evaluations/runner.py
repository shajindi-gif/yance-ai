import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.services.evaluations.contracts import (
    DIMENSIONS,
    EVAL_TYPES,
    CaseExecution,
    DatasetExecution,
    DimensionResult,
    EvalType,
)
from app.services.evaluations.loader import LoadedDataset, load_dataset
from app.services.evaluations.scorers import score_output
from app.services.evaluations.targets import execute_target


def _canonical_hash(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def execute_dataset(dataset: LoadedDataset) -> DatasetExecution:
    results = []
    for case in dataset.cases:
        started = perf_counter()
        try:
            output = execute_target(case)
            result = score_output(case, output, dataset.card)
        except Exception as exc:
            result = CaseExecution(
                case_id=case.case_id,
                status="error",
                dimensions=[
                    DimensionResult(
                        dimension=dimension,
                        score=0,
                        is_applicable=True,
                        rationale="Execution error remains in the metric denominator.",
                    )
                    for dimension in DIMENSIONS
                ],
                error_types=["execution_error"],
                error_code="eval_case_execution_failed",
                safe_error_message=f"{type(exc).__name__}: evaluation target failed",
                passed=False,
            )
        result.latency_ms = max(0, round((perf_counter() - started) * 1000))
        results.append(result)
    return DatasetExecution(
        dataset=dataset.card,
        content_sha256=dataset.content_sha256,
        cases=list(dataset.cases),
        results=results,
        requested_cases=len(dataset.cases),
        completed_cases=sum(item.status == "completed" for item in results),
        passed_cases=sum(item.passed for item in results),
        error_cases=sum(item.status == "error" for item in results),
        total_latency_ms=sum(item.latency_ms for item in results),
        total_cost_usd=sum(item.cost_usd for item in results),
        release_gate_passed=all(item.passed for item in results),
    )


def execute_bundle(root: Path, eval_types: list[EvalType] | None = None) -> list[DatasetExecution]:
    selected = eval_types or list(EVAL_TYPES)
    return [execute_dataset(load_dataset(root, eval_type)) for eval_type in selected]


def _sync_dataset(db: Session, execution: DatasetExecution) -> tuple[EvalDatasetVersion, list[EvalCase]]:
    card = execution.dataset
    dataset = db.scalar(select(EvalDataset).where(EvalDataset.key == card.key))
    if dataset and dataset.eval_type != card.eval_type:
        raise ValueError(f"dataset key {card.key} already belongs to another eval type")
    if not dataset:
        dataset = EvalDataset(
            key=card.key,
            name=card.name,
            eval_type=card.eval_type,
            description=card.description,
            status="draft" if card.review_status == "unreviewed" else card.review_status,
            data_classification=card.data_classification,
            is_demo=card.is_demo,
        )
        db.add(dataset)
        db.flush()
    else:
        dataset.name = card.name
        dataset.description = card.description
        dataset.status = "draft" if card.review_status == "unreviewed" else card.review_status
        dataset.data_classification = card.data_classification
        dataset.is_demo = card.is_demo

    version = db.scalar(
        select(EvalDatasetVersion).where(
            EvalDatasetVersion.dataset_id == dataset.id,
            EvalDatasetVersion.version == card.version,
        )
    )
    if version and version.content_sha256 != execution.content_sha256:
        raise ValueError(f"dataset {card.key}@{card.version} is immutable; create a new version")
    if not version:
        version = EvalDatasetVersion(
            dataset_id=dataset.id,
            version=card.version,
            content_sha256=execution.content_sha256,
            case_count=execution.requested_cases,
            target_key=card.target_key,
            target_version=card.target_version,
            scorer_version=card.scorer_version,
            review_status=card.review_status,
            card_json=card.model_dump(mode="json"),
        )
        db.add(version)
        db.flush()
        for case in execution.cases:
            payload = case.model_dump(mode="json")
            db.add(
                EvalCase(
                    dataset_version_id=version.id,
                    case_id=case.case_id,
                    eval_type=case.eval_type,
                    question=case.question,
                    input_json=case.input,
                    ground_truth_json=case.ground_truth,
                    expected_evidence_json=[item.model_dump(mode="json") for item in case.expected_evidence],
                    tags_json=case.tags,
                    risk_tier=case.risk_tier,
                    reference_date=case.reference_date,
                    content_sha256=_canonical_hash(payload),
                )
            )
        db.flush()
    cases = list(
        db.scalars(
            select(EvalCase)
            .where(EvalCase.dataset_version_id == version.id)
            .order_by(EvalCase.case_id)
        ).all()
    )
    if len(cases) != execution.requested_cases:
        raise ValueError(f"dataset {card.key}@{card.version} case count does not match persisted version")
    return version, cases


def persist_executions(
    db: Session,
    executions: list[DatasetExecution],
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[EvalRun]:
    batch_id = uuid.uuid4()
    runs = []
    for execution in executions:
        version, cases = _sync_dataset(db, execution)
        case_by_key = {item.case_id: item for item in cases}
        now = datetime.now(UTC)
        run = EvalRun(
            tenant_id=tenant_id,
            batch_id=batch_id,
            dataset_version_id=version.id,
            created_by=user_id,
            eval_type=execution.dataset.eval_type,
            status="running",
            target_key=execution.dataset.target_key,
            target_version=execution.dataset.target_version,
            scorer_version=execution.dataset.scorer_version,
            model="internal-deterministic",
            prompt_version=None,
            is_demo=execution.dataset.is_demo,
            requested_cases=execution.requested_cases,
            config_json={
                "thresholds": execution.dataset.thresholds,
                "review_status": execution.dataset.review_status,
                "data_classification": execution.dataset.data_classification,
            },
            started_at=now,
        )
        db.add(run)
        db.flush()
        for result in execution.results:
            evaluation = Evaluation(
                tenant_id=tenant_id,
                eval_run_id=run.id,
                eval_case_id=case_by_key[result.case_id].id,
                status=result.status,
                model_answer_json=result.model_answer,
                overall_score=result.overall_score,
                passed=result.passed,
                hallucination_detected=result.hallucination_detected,
                error_types_json=result.error_types,
                latency_ms=result.latency_ms,
                cost_usd=result.cost_usd,
            )
            db.add(evaluation)
            db.flush()
            for dimension in result.dimensions:
                db.add(
                    EvaluationDimensionScore(
                        tenant_id=tenant_id,
                        evaluation_id=evaluation.id,
                        dimension=dimension.dimension,
                        score=dimension.score,
                        is_applicable=dimension.is_applicable,
                        scorer="deterministic",
                        scorer_version=execution.dataset.scorer_version,
                        rationale=dimension.rationale,
                    )
                )
            for evidence in result.evidence:
                db.add(
                    EvaluationEvidence(
                        tenant_id=tenant_id,
                        evaluation_id=evaluation.id,
                        expectation=evidence.expectation,
                        observed=evidence.observed,
                        source_reference=evidence.source_reference,
                        passed=evidence.passed,
                    )
                )
            if result.status == "error":
                db.add(
                    EvaluationError(
                        tenant_id=tenant_id,
                        eval_run_id=run.id,
                        evaluation_id=evaluation.id,
                        case_id=result.case_id,
                        code=result.error_code or "eval_case_execution_failed",
                        error_type=(result.error_types or ["execution_error"])[0],
                        safe_message=result.safe_error_message or "Evaluation case failed",
                    )
                )
        run.status = "completed"
        run.completed_cases = execution.completed_cases
        run.passed_cases = execution.passed_cases
        run.error_cases = execution.error_cases
        run.total_latency_ms = execution.total_latency_ms
        run.total_cost_usd = execution.total_cost_usd
        run.release_gate_passed = execution.release_gate_passed
        run.finished_at = datetime.now(UTC)
        runs.append(run)
    db.commit()
    return runs
