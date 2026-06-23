"""Demo-data seed: populates a realistic history and is idempotent per user."""
from datetime import date, timedelta

from backend.demo.seed import seed_demo_for_user
from backend.persistence import repository


def test_seed_populates_and_is_idempotent(client, session_factory):
    # `client` registers user-a; seed that user by id.
    s = session_factory()
    user = repository.get_user_by_email(s, "user-a@example.com")
    seed_demo_for_user(s, user.id)

    s2 = session_factory()
    assert repository.get_profile(s2, user.id) is not None
    assert repository.get_macro_target(s2, user.id) is not None
    settings = repository.get_settings(s2, user.id)
    assert settings is not None and settings.country == "Germany"

    weigh_ins = repository.list_weigh_ins(s2, user.id)
    assert len(weigh_ins) > 30
    # Food logs span most of the last ~45 days (a few days are intentionally skipped).
    intake = repository.daily_intake(s2, user.id, date.today() - timedelta(days=46), date.today())
    assert len(intake) > 30
    sessions = repository.list_workout_sessions(s2, user.id)
    assert len(sessions) >= 10
    assert sum(len(ws.sets) for ws in sessions) > 0
    assert len(repository.list_measurements(s2, user.id)) >= 3
    foods_n = len(repository.list_foods(s2, user.id, limit=500))
    assert foods_n >= 10

    # Idempotent: a second seed refreshes, it does not duplicate.
    seed_demo_for_user(s2, user.id)
    s3 = session_factory()
    assert len(repository.list_foods(s3, user.id, limit=500)) == foods_n
    assert len(repository.list_weigh_ins(s3, user.id)) == len(weigh_ins)
    assert len(repository.list_workout_sessions(s3, user.id)) == len(sessions)


def test_seed_is_user_scoped(client, second_client, session_factory):
    """Seeding user-a must not create any rows for user-b."""
    s = session_factory()
    a = repository.get_user_by_email(s, "user-a@example.com")
    b = repository.get_user_by_email(s, "user-b@example.com")
    seed_demo_for_user(s, a.id)

    s2 = session_factory()
    assert repository.get_profile(s2, b.id) is None
    assert repository.list_weigh_ins(s2, b.id) == []
    assert repository.list_workout_sessions(s2, b.id) == []
    assert repository.list_foods(s2, b.id, limit=500) == []
