"""Demo cleanup: removes aged demo users + all their rows; spares fresh demos and real users."""
from datetime import datetime, timedelta, timezone

from backend.cleanup_demos import cleanup_demos
from backend.demo.seed import seed_demo_for_user
from backend.persistence import repository
from backend.persistence.models import User


def test_cleanup_removes_only_aged_demo_users(client, session_factory):
    s = session_factory()
    # Two demo users (one will be aged) + the real user-a from the `client` fixture.
    old = repository.create_user(s, email="demo-old@demo.invalid", password_hash="x", is_demo=True)
    fresh = repository.create_user(s, email="demo-fresh@demo.invalid", password_hash="x", is_demo=True)
    seed_demo_for_user(s, old.id)  # give the aged user real rows to prove the cascade
    # Backdate the aged user beyond the TTL.
    s.get(User, old.id).created_at = datetime.now(timezone.utc) - timedelta(hours=5)
    s.commit()

    removed = cleanup_demos(s, ttl_hours=3)
    s.commit()
    assert removed == 1

    s2 = session_factory()
    assert repository.get_user(s2, old.id) is None
    assert repository.list_weigh_ins(s2, old.id) == []  # rows cascaded away
    assert repository.list_workout_sessions(s2, old.id) == []
    assert repository.get_user(s2, fresh.id) is not None  # fresh demo kept
    assert repository.get_user_by_email(s2, "user-a@example.com") is not None  # real user untouched
