"""Exercise SIGTERM on empty local *_test databases, never a production worker."""

import json
import os
import selectors
import signal
import subprocess
import sys
from time import monotonic

import psycopg
from sqlalchemy.engine import make_url


def main():
    url = make_url(os.environ["DATABASE_URL"])
    if (
        os.environ.get("APP_ENV") != "test"
        or url.host not in {"127.0.0.1", "localhost"}
        or not url.database
        or not url.database.endswith("_test")
        or "prod" in url.database.lower()
    ):
        raise SystemExit("Only explicitly configured local *_test databases are allowed")
    with psycopg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False)
    ) as db:
        if db.execute("SELECT count(*) FROM agent_runs").fetchone()[0]:
            raise SystemExit("Use a new empty migrated test database; do not delete existing tasks")
    env = dict(os.environ, EMAIL_ENABLED="false", LLM_DEFAULT_PROVIDER="mock", PYTHONUNBUFFERED="1")
    outcomes = []
    for worker in ("agent_worker", "notification_worker"):
        process = subprocess.Popen(
            [sys.executable, "-m", f"app.workers.{worker}", "--poll-seconds", "0.1"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        output = ""
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                deadline = monotonic() + 20
                while f"{worker}_started" not in output and monotonic() < deadline:
                    if selector.select(timeout=0.25):
                        line = process.stdout.readline()
                        if not line:
                            break
                        output += line
            if f"{worker}_started" not in output:
                raise RuntimeError(f"{worker} did not start")
            process.send_signal(signal.SIGTERM)
            remainder, _ = process.communicate(timeout=20)
            output += remainder
            passed = process.returncode == 0 and f"{worker}_stopped" in output
            if worker == "agent_worker":
                passed = passed and "SIGTERM" in output
            outcomes.append(
                {"worker": worker, "exit_code": process.returncode, "sigterm_passed": passed}
            )
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate(timeout=5)
    print(json.dumps({"results": outcomes, "external_email_enabled": False}))
    return 0 if all(row["sigterm_passed"] for row in outcomes) else 1


if __name__ == "__main__":
    raise SystemExit(main())
