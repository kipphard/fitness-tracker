"""Create a user account manually (public registration is disabled in production).

Usage:
    python -m backend.create_user <email> <password>
"""
from __future__ import annotations

import sys

from backend.auth.security import hash_password
from backend.persistence import repository
from backend.persistence.database import SessionLocal


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: python -m backend.create_user <email> <password>")
        return 1
    email = argv[0].strip().lower()
    password = argv[1]

    session = SessionLocal()
    try:
        if repository.get_user_by_email(session, email) is not None:
            print(f"user {email} already exists")
            return 1
        user = repository.create_user(
            session, email=email, password_hash=hash_password(password)
        )
        session.commit()
        print(f"created user {email} (id={user.id})")
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
