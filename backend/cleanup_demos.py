"""Delete expired demo sandboxes (live demo).

Removes every ``is_demo`` user whose ``created_at`` is older than ``DEMO_TTL_HOURS`` (default 3),
and — via :func:`repository.delete_user` — all of their rows. Real users are never touched.

Run manually:
    python -m backend.cleanup_demos

Cron (every 30 minutes), loading the server .env for DATABASE_URL / FERNET_KEY:
    */30 * * * * cd /opt/fitness-tracker && set -a && . ./.env && set +a && \
        .venv/bin/python -m backend.cleanup_demos >> /var/log/demo-cleanup.log 2>&1
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.config import get_settings
from backend.persistence import repository
from backend.persistence.database import SessionLocal
from backend.persistence.models import User


def cleanup_demos(
    session: Session, *, ttl_hours: int, now: datetime | None = None
) -> int:
    """Delete demo users older than ``ttl_hours`` (and their rows). Returns how many were removed.
    Caller commits."""
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=ttl_hours)
    ids = list(
        session.scalars(
            select(User.id).where(User.is_demo.is_(True), User.created_at < cutoff)
        )
    )
    for user_id in ids:
        repository.delete_user(session, user_id)
    session.flush()
    return len(ids)


def main() -> int:
    settings = get_settings()
    session = SessionLocal()
    try:
        n = cleanup_demos(session, ttl_hours=settings.demo_ttl_hours)
        session.commit()
    finally:
        session.close()
    print(f"deleted {n} expired demo user(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
