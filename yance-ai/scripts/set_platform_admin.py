"""Grant or revoke platform administration from a trusted server shell."""

import argparse

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models.models import Tenant, User


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", required=True)
    parser.add_argument("--tenant-slug", required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--grant", action="store_true")
    action.add_argument("--revoke", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(
            select(User)
            .join(Tenant, Tenant.id == User.tenant_id)
            .where(User.email == args.email.lower(), Tenant.slug == args.tenant_slug)
        )
        if not user:
            raise SystemExit("No exact user and tenant match found")
        user.is_platform_admin = bool(args.grant)
        db.commit()
        state = "granted" if user.is_platform_admin else "revoked"
        print(f"Platform administration {state} for {user.email} in {args.tenant_slug}")


if __name__ == "__main__":
    main()
