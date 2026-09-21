import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.core.db import SessionLocal
from app.main import app
from app.models.models import EvalDataset, EvalDatasetVersion, EvalRun, User
from app.services.evaluations.contracts import EVAL_TYPES
from app.services.evaluations.loader import load_dataset
from app.services.evaluations.runner import execute_bundle, execute_dataset, persist_executions

DATASET_ROOT = Path("evals/datasets")


def _register(client: TestClient, prefix: str) -> tuple[dict[str, str], str]:
    email = f"eval-{prefix}@example.com"
    response = client.post(
        "/api/v1/auth/register",
        json={
            "company_name": f"Eval {prefix}",
            "industry": "人工智能",
            "province": "上海市",
            "city": "上海市",
            "owner_name": "Eval Owner",
            "owner_email": email,
            "owner_password": "integration-password-123",
            "agreed_terms_version": "test-terms",
        },
    )
    assert response.status_code == 201, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}, email


def test_five_part_bundle_executes_actual_targets_and_release_gate():
    executions = execute_bundle(DATASET_ROOT)
    assert [item.dataset.eval_type for item in executions] == list(EVAL_TYPES)
    assert sum(item.requested_cases for item in executions) == 11
    assert sum(item.completed_cases for item in executions) == 11
    assert sum(item.error_cases for item in executions) == 0
    assert all(item.release_gate_passed for item in executions)
    assert {item.dataset.review_status for item in executions} == {"unreviewed"}
    assert {item.dataset.data_classification for item in executions} == {"synthetic"}
    citation = next(item for item in executions if item.dataset.eval_type == "citation_eval")
    unsupported = next(
        item for item in citation.results if item.case_id == "citation-missing-negative-002"
    )
    assert unsupported.model_answer["support"] == {"claim-amount": False}
    assert unsupported.evidence[0].observed == "exact quote not found"
    assert unsupported.evidence[0].passed is True


def test_execution_errors_remain_case_and_dimension_denominators(monkeypatch):
    dataset = load_dataset(DATASET_ROOT, "policy_retrieval_eval")

    def fail_target(_case):
        raise RuntimeError("raw provider details must not be returned")

    monkeypatch.setattr("app.services.evaluations.runner.execute_target", fail_target)
    result = execute_dataset(dataset)
    assert result.requested_cases == 2
    assert result.completed_cases == 0
    assert result.error_cases == 2
    assert result.passed_cases == 0
    assert result.release_gate_passed is False
    assert all(item.status == "error" for item in result.results)
    assert all(len(item.dimensions) == 6 for item in result.results)
    assert all(score.score == 0 for item in result.results for score in item.dimensions)
    assert all("raw provider details" not in (item.safe_error_message or "") for item in result.results)


def test_platform_admin_executes_persists_and_drills_into_evaluations():
    with SessionLocal() as db:
        db.execute(delete(EvalRun))
        db.execute(delete(EvalDataset))
        db.commit()
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        platform_headers, platform_email = _register(client, f"platform-{suffix}")
        tenant_headers, _ = _register(client, f"tenant-{suffix}")
        with SessionLocal() as db:
            platform_user = db.scalar(select(User).where(User.email == platform_email))
            assert platform_user
            platform_user.is_platform_admin = True
            db.commit()

        denied = client.post(
            "/api/v1/admin/evals/runs", headers=tenant_headers, json={"eval_type": "all"}
        )
        assert denied.status_code == 403

        empty = client.get(
            "/api/v1/admin/evals/overview?eval_type=hallucination_eval",
            headers=platform_headers,
        )
        assert empty.status_code == 200
        assert empty.json()["available"] is False
        assert empty.json()["message"] == "No evaluation data yet."
        assert all(value is None for value in empty.json()["cards"].values())

        created = client.post(
            "/api/v1/admin/evals/runs", headers=platform_headers, json={"eval_type": "all"}
        )
        assert created.status_code == 201, created.text
        payload = created.json()
        assert payload["release_gate_passed"] is True
        assert len(payload["runs"]) == 5
        assert sum(item["requested_cases"] for item in payload["runs"]) == 11
        assert sum(item["error_cases"] for item in payload["runs"]) == 0

        overview = client.get("/api/v1/admin/evals/overview", headers=platform_headers)
        assert overview.status_code == 200, overview.text
        metrics = overview.json()
        assert metrics["available"] is True
        assert metrics["cards"]["accuracy"] == 1
        assert metrics["cards"]["citation_accuracy"] == 1
        assert metrics["cards"]["hallucination_rate"] == 0
        assert metrics["cards"]["pass_rate"] == 1
        assert metrics["cards"]["average_cost_usd"] == 0
        assert metrics["counts"] == {
            "requested": 11,
            "completed": 11,
            "passed": 11,
            "errors": 0,
        }
        assert metrics["investor_quality_eligible"] is False
        assert {item["review_status"] for item in metrics["runs"]} == {"unreviewed"}

        resources = client.get("/api/v1/admin/resources/evals", headers=platform_headers)
        assert resources.status_code == 200
        assert resources.json()["total"] == 5

        run_id = payload["runs"][0]["id"]
        detail = client.get(f"/api/v1/admin/evals/runs/{run_id}", headers=platform_headers)
        assert detail.status_code == 200, detail.text
        trace = detail.json()
        assert trace["dataset"]["review_status"] == "unreviewed"
        assert trace["dataset"]["data_classification"] == "synthetic"
        assert trace["cases"]
        assert set(trace["cases"][0]) >= {
            "question",
            "ground_truth",
            "model_answer",
            "overall_score",
            "evidence",
            "error_types",
        }
        assert len(trace["cases"][0]["dimensions"]) == 6

        repeated = client.post(
            "/api/v1/admin/evals/runs",
            headers=platform_headers,
            json={"eval_type": "eligibility_eval"},
        )
        assert repeated.status_code == 201
        latest_only = client.get("/api/v1/admin/evals/overview", headers=platform_headers).json()
        assert latest_only["counts"]["requested"] == 11

        investor = client.get("/api/v1/admin/investor-metrics", headers=platform_headers)
        assert investor.status_code == 200
        assert investor.json()["availability"]["evaluation_metrics"] is False


def test_dataset_version_content_is_immutable():
    suffix = uuid.uuid4().hex
    with TestClient(app) as client:
        headers, email = _register(client, f"immutable-{suffix}")
        with SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            assert user
            execution = execute_bundle(DATASET_ROOT, ["citation_eval"])[0]
            persist_executions(db, [execution], tenant_id=user.tenant_id, user_id=user.id)
            version = db.scalar(
                select(EvalDatasetVersion).where(
                    EvalDatasetVersion.content_sha256 == execution.content_sha256
                )
            )
            assert version
            modified = execution.model_copy(update={"content_sha256": "f" * 64})
            with pytest.raises(ValueError, match="immutable"):
                persist_executions(db, [modified], tenant_id=user.tenant_id, user_id=user.id)
            db.rollback()
        assert headers
