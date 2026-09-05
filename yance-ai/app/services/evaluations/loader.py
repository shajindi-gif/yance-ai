import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from app.services.evaluations.contracts import DatasetCard, EvalCaseContract, EvalType


@dataclass(frozen=True)
class LoadedDataset:
    card: DatasetCard
    cases: tuple[EvalCaseContract, ...]
    content_sha256: str


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _load_jsonl(path: Path) -> list[dict]:
    if path.stat().st_size > 10 * 1024 * 1024:
        raise ValueError(f"{path}: dataset exceeds the 10 MiB safety limit")
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON") from exc
    if len(rows) > 1000:
        raise ValueError(f"{path}: dataset exceeds the 1000-case execution limit")
    return rows


def load_dataset(root: Path, eval_type: EvalType) -> LoadedDataset:
    directory = root / eval_type
    card_path = directory / "dataset.json"
    cases_path = directory / "cases.jsonl"
    if not card_path.is_file() or not cases_path.is_file():
        raise ValueError(f"dataset files missing for {eval_type}")
    card = DatasetCard.model_validate_json(card_path.read_text(encoding="utf-8"))
    if card.eval_type != eval_type:
        raise ValueError(f"dataset eval_type mismatch for {eval_type}")
    rows = _load_jsonl(cases_path)
    cases = tuple(EvalCaseContract.model_validate(row) for row in rows)
    if not cases:
        raise ValueError(f"dataset {card.key} has no cases")
    ids = [case.case_id for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError(f"dataset {card.key} contains duplicate case_id")
    for case in cases:
        if case.eval_type != card.eval_type or case.dataset_version != card.version:
            raise ValueError(f"case {case.case_id} does not match dataset type/version")
    payload = {
        "card": card.model_dump(mode="json"),
        "cases": [case.model_dump(mode="json") for case in cases],
    }
    return LoadedDataset(
        card=card,
        cases=cases,
        content_sha256=hashlib.sha256(_canonical(payload)).hexdigest(),
    )
