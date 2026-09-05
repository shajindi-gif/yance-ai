from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    EvalDataset,
    EvalDatasetVersion,
    EvalRun,
    Evaluation,
    EvaluationDimensionScore,
)
from app.services.evaluations.contracts import DIMENSIONS, EVAL_TYPES, EvalType


def _mean(values: list[float]) -> float | None:
    return round(sum(values) / len(values), 6) if values else None


def _latest_runs(db: Session, eval_type: EvalType | None = None) -> list[EvalRun]:
    query = select(EvalRun).where(EvalRun.status == "completed", EvalRun.is_demo.is_(False))
    if eval_type:
        query = query.where(EvalRun.eval_type == eval_type)
    runs = db.scalars(query.order_by(EvalRun.finished_at.desc(), EvalRun.created_at.desc())).all()
    latest = {}
    for run in runs:
        latest.setdefault(run.eval_type, run)
    return list(latest.values())


def evaluation_overview(db: Session, eval_type: EvalType | None = None) -> dict:
    runs = _latest_runs(db, eval_type)
    if not runs:
        return {
            "available": False,
            "message": "No evaluation data yet.",
            "generated_at": datetime.now(UTC).isoformat(),
            "scope": "latest_completed_non_demo_run_per_eval_type",
            "cards": {
                "accuracy": None,
                "citation_accuracy": None,
                "hallucination_rate": None,
                "pass_rate": None,
                "average_latency_ms": None,
                "average_cost_usd": None,
            },
            "counts": {"requested": 0, "completed": 0, "passed": 0, "errors": 0},
            "dimensions": [],
            "runs": [],
            "investor_quality_eligible": False,
        }
    run_ids = [run.id for run in runs]
    evaluations = list(
        db.scalars(select(Evaluation).where(Evaluation.eval_run_id.in_(run_ids))).all()
    )
    evaluation_ids = [item.id for item in evaluations]
    scores = list(
        db.scalars(
            select(EvaluationDimensionScore).where(
                EvaluationDimensionScore.evaluation_id.in_(evaluation_ids),
                EvaluationDimensionScore.is_applicable.is_(True),
                EvaluationDimensionScore.score.is_not(None),
            )
        ).all()
    )
    by_dimension = {
        dimension: [float(item.score) for item in scores if item.dimension == dimension]
        for dimension in DIMENSIONS
    }
    requested = sum(run.requested_cases for run in runs)
    passed = sum(run.passed_cases for run in runs)
    version_rows = {
        version.id: (version, dataset)
        for version, dataset in db.execute(
            select(EvalDatasetVersion, EvalDataset)
            .join(EvalDataset, EvalDataset.id == EvalDatasetVersion.dataset_id)
            .where(EvalDatasetVersion.id.in_([run.dataset_version_id for run in runs]))
        ).all()
    }
    run_rows = []
    for run in sorted(runs, key=lambda item: item.eval_type):
        version, dataset = version_rows[run.dataset_version_id]
        run_rows.append(
            {
                "id": str(run.id),
                "batch_id": str(run.batch_id),
                "eval_type": run.eval_type,
                "dataset": dataset.name,
                "dataset_key": dataset.key,
                "dataset_version": version.version,
                "review_status": version.review_status,
                "data_classification": dataset.data_classification,
                "target_key": run.target_key,
                "target_version": run.target_version,
                "scorer_version": run.scorer_version,
                "requested_cases": run.requested_cases,
                "completed_cases": run.completed_cases,
                "passed_cases": run.passed_cases,
                "error_cases": run.error_cases,
                "release_gate_passed": run.release_gate_passed,
                "finished_at": run.finished_at,
            }
        )
    hallucination_safety = _mean(by_dimension["hallucination"])
    total_latency = sum(item.latency_ms for item in evaluations)
    total_cost = sum(float(item.cost_usd or 0) for item in evaluations)
    return {
        "available": True,
        "message": None,
        "generated_at": datetime.now(UTC).isoformat(),
        "scope": "latest_completed_non_demo_run_per_eval_type",
        "cards": {
            "accuracy": _mean(by_dimension["correctness"]),
            "citation_accuracy": _mean(by_dimension["citation_accuracy"]),
            "hallucination_rate": None
            if hallucination_safety is None
            else round(1 - hallucination_safety, 6),
            "pass_rate": round(passed / requested, 6) if requested else None,
            "average_latency_ms": round(total_latency / requested, 3) if requested else None,
            "average_cost_usd": round(total_cost / requested, 6) if requested else None,
        },
        "counts": {
            "requested": requested,
            "completed": sum(run.completed_cases for run in runs),
            "passed": passed,
            "errors": sum(run.error_cases for run in runs),
        },
        "dimensions": [
            {"dimension": dimension, "score": _mean(values), "sample_size": len(values)}
            for dimension, values in by_dimension.items()
        ],
        "runs": run_rows,
        "investor_quality_eligible": {item["eval_type"] for item in run_rows} == set(EVAL_TYPES)
        and all(item["review_status"] == "reviewed" for item in run_rows),
    }
