import argparse
import json
from pathlib import Path


def load_cases(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def validate_case(case: dict) -> list[str]:
    errors = []
    for key in ("id", "input", "expected", "tags"):
        if key not in case:
            errors.append(f"{case.get('id', '<unknown>')}: missing {key}")
    if "eligible" not in case.get("expected", {}):
        errors.append(f"{case.get('id', '<unknown>')}: expected.eligible is required")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", required=True, type=Path)
    args = parser.parse_args()
    cases = load_cases(args.cases)
    errors = [error for case in cases for error in validate_case(case)]
    print(
        json.dumps(
            {"cases": len(cases), "passed": len(cases) - len(errors), "errors": errors},
            ensure_ascii=False,
        )
    )
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
