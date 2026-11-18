"""Offline model adapter for real local browser→API→DB acceptance only.

This module is never imported by production. Fixtures are explicitly synthetic.
"""

import json
import os

from sqlalchemy.engine import make_url

if os.environ.get("APP_ENV") != "test" or os.environ.get("LLM_DEFAULT_PROVIDER") != "mock":
    raise RuntimeError("Browser fixture requires test + mock")
url = make_url(os.environ.get("DATABASE_URL", ""))
if (url.host not in {"localhost", "127.0.0.1"} or not url.database or
    not url.database.endswith("_test") or "prod" in url.database or
    os.environ.get("YANCE_TEST_DATABASE_ACK") != url.database):
    raise RuntimeError("Explicit loopback disposable database acknowledgement required")

from app.api.routes.workspace import gateway  # noqa: E402
from app.services.llm.base import LLMResponse  # noqa: E402
from tests.run_browser_api import app  # noqa: E402, F401


class SyntheticModel:
    async def complete(self, request):
        payload = json.loads(request.messages[-1]["content"])
        source = payload["sources"][0]
        quote = source["policy_quote"]
        return LLMResponse(
            content=json.dumps(
                {"claims": [{"text": quote, "source": source["index"], "policy_quote": quote}]},
                ensure_ascii=False,
            ),
            provider="mock",
            model="synthetic-evidence-extract",
        )


gateway.providers["mock"] = SyntheticModel()
