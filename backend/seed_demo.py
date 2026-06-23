"""Seed a standing account with demo data (e.g. a preview account).

Usage:
    python -m backend.seed_demo <email> [password]

Find-or-create the user, then run the generative demo seed. Idempotent: re-running refreshes the
same dataset. The public per-visitor demo uses ``seed_demo_for_user`` directly via /api/auth/demo;
this CLI is for a standing preview account you can log into and inspect.
"""
from __future__ import annotations

import sys

from backend.auth.security import hash_password
from backend.demo.seed import seed_demo_for_user
from backend.persistence import repository
from backend.persistence.database import SessionLocal


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: python -m backend.seed_demo <email> [password]")
        return 1
    email = argv[0].strip().lower()
    password = argv[1] if len(argv) > 1 else "demo1234"

    session = SessionLocal()
    try:
        user = repository.get_user_by_email(session, email)
        if user is None:
            user = repository.create_user(
                session, email=email, password_hash=hash_password(password)
            )
            session.commit()
            print(f"created user {email}")
        seed_demo_for_user(session, user.id)
        print(f"seeded demo data for {email} (id={user.id})")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
