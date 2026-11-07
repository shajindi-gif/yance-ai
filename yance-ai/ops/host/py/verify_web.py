#!/usr/bin/env python3
"""verify_web.py — prove that collected text is actually retrievable through the API.

"Saving the original file" is not delivery.  The acceptance test is that a *normal*
authenticated account — the same principal the web UI uses — gets the collected
chunks back from ``GET /api/v1/policies/evidence-search``.

Authentication paths, in order of preference:

1. ``--token`` / ``$YANCE_VERIFY_TOKEN``: an existing bearer token (copy one from
   the browser devtools of a logged-in user);
2. ``--email`` + password on stdin: a real password login through ``/auth/login``.

The script never invents a user, never uses a superuser shortcut, and never prints
the token or the password.

Exit codes: 0 retrievable, 4 authenticated but nothing found, 5 authentication
failed, 6 endpoint error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import httpx


def get_token(client: httpx.Client, args: argparse.Namespace) -> str | None:
    token = args.token or os.environ.get("YANCE_VERIFY_TOKEN", "")
    if token:
        print("auth: using supplied bearer token")
        return token.strip()

    if not args.email:
        print(
            "auth: no token and no --email given\n"
            "      pass --token <bearer from a logged-in user> or --email you@example.com "
            "and pipe the password on stdin",
            file=sys.stderr,
        )
        return None

    password = sys.stdin.readline().rstrip("\n")
    if not password:
        print("auth: empty password on stdin", file=sys.stderr)
        return None

    headers = {}
    if args.tenant_slug:
        headers["X-Tenant-Slug"] = args.tenant_slug
    response = client.post(
        "/api/v1/auth/login",
        data={"username": args.email, "password": password},
        headers=headers,
    )
    if response.status_code != 200:
        print(f"auth: login failed HTTP {response.status_code}: {response.text[:200]}", file=sys.stderr)
        return None
    payload = response.json()
    print(f"auth: password login ok for {args.email}")
    return payload.get("access_token")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default=os.environ.get("PROD_API_BASE", "http://127.0.0.1:8000"))
    parser.add_argument("--query", default="知识产权")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--token", default="")
    parser.add_argument("--email", default="")
    parser.add_argument("--tenant-slug", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    with httpx.Client(base_url=args.base_url.rstrip("/"), timeout=30.0) as client:
        if not args.token and not os.environ.get("YANCE_VERIFY_TOKEN"):
            print("password is read from stdin (never from argv)", file=sys.stderr)
        token = get_token(client, args)
        if not token:
            return 5

        headers = {"Authorization": f"Bearer {token}"}
        response = client.get(
            "/api/v1/policies/evidence-search",
            params={"q": args.query, "limit": args.limit},
            headers=headers,
        )
        if response.status_code == 401:
            print("endpoint: 401 invalid or expired token", file=sys.stderr)
            return 5
        if response.status_code != 200:
            print(f"endpoint: HTTP {response.status_code}: {response.text[:300]}", file=sys.stderr)
            return 6

        data = response.json()
        if args.json:
            print(json.dumps(data, ensure_ascii=False, indent=2))
        else:
            corpus = data.get("corpus", {})
            print(f"query          : {data.get('query')}")
            print(f"retrieval      : {data.get('retrieval')}")
            print(f"hits           : {data.get('count')}")
            print(f"corpus         : {json.dumps(corpus, ensure_ascii=False)}")
            for index, hit in enumerate(data.get("hits", [])[:3], 1):
                print(f"  [{index}] {hit.get('policy_title')}")
                print(f"      status={hit.get('policy_status')} chars={hit.get('char_start')}-{hit.get('char_end')}")
                snippet = (hit.get("chunk_content") or "").replace("\n", " ")[:90]
                print(f"      {snippet}")

    if data.get("count", 0) < 1:
        print(
            "\nRESULT: authenticated request succeeded but returned no hits.\n"
            "        Original files may exist on disk while the corpus is still not\n"
            "        searchable — check policy status (collected/published) and chunks.",
            file=sys.stderr,
        )
        return 4

    print("\nRESULT: collected content is retrievable by a normal user through the API")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
