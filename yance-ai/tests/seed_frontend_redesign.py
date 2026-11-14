"""Extend the guarded V2 fixture with a source-grounded synthetic review project."""
import json
import sys
from pathlib import Path

from seed_v2_browser import main as seed_workspace


def main():
    # Applies test environment, database acknowledgement and private output guards.
    seed_workspace()
    from fastapi.testclient import TestClient
    from test_v2_suggestion_evidence import _project

    from app.main import app

    with TestClient(app) as client:
        headers, _, application_id, _, _, _ = _project(client)
    output = Path(sys.argv[1]).resolve()
    data = json.loads(output.read_text())
    data.update(
        export_token=headers["Authorization"].removeprefix("Bearer "),
        export_application_id=application_id,
    )
    output.write_text(json.dumps(data))
    output.chmod(0o600)
    print("Synthetic review/export fixture ready")


if __name__ == "__main__":
    main()
