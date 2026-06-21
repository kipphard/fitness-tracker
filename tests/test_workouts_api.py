"""Exercises, routines, sessions, sets, and progression API tests."""
from decimal import Decimal


def _exercise(client, name="Barbell Bench Press"):
    return next(e for e in client.get("/api/exercises").json() if e["name"] == name)


def test_library_seeded_and_search(client):
    res = client.get("/api/exercises", params={"q": "bench"}).json()
    assert any("Bench" in e["name"] for e in res)
    all_exercises = client.get("/api/exercises").json()
    assert len(all_exercises) >= 20
    assert all(e["source"] in ("lib", "custom") for e in all_exercises)


def test_create_custom_exercise(client):
    created = client.post(
        "/api/exercises",
        json={"name": "Cable Fly", "primary_muscles": ["chest"], "equipment": "cable"},
    ).json()
    assert created["source"] == "custom"
    assert created["name"] == "Cable Fly"
    found = client.get("/api/exercises", params={"q": "cable fly"}).json()
    assert any(x["id"] == created["id"] for x in found)


def test_routine_crud(client):
    bench = _exercise(client)
    squat = _exercise(client, "Barbell Back Squat")
    routine = client.post(
        "/api/routines",
        json={
            "name": "Upper",
            "exercises": [
                {"exercise_id": bench["id"], "planned_sets": 3, "planned_reps": 8},
                {"exercise_id": squat["id"], "planned_sets": 5},
            ],
        },
    ).json()
    assert routine["name"] == "Upper"
    assert len(routine["exercises"]) == 2
    assert routine["exercises"][0]["exercise_name"] == "Barbell Bench Press"
    assert routine["exercises"][0]["planned_reps"] == 8

    assert any(x["id"] == routine["id"] for x in client.get("/api/routines").json())
    assert client.delete(f"/api/routines/{routine['id']}").status_code == 204
    assert client.get(f"/api/routines/{routine['id']}").status_code == 404


def test_session_log_sets_and_finish(client):
    bench = _exercise(client)
    sid = client.post("/api/workouts", json={}).json()["id"]

    s1 = client.post(
        f"/api/workouts/{sid}/sets",
        json={"exercise_id": bench["id"], "weight": "100", "reps": 5},
    ).json()
    assert s1["set_index"] == 1
    s2 = client.post(
        f"/api/workouts/{sid}/sets",
        json={"exercise_id": bench["id"], "weight": "100", "reps": 5},
    ).json()
    assert s2["set_index"] == 2

    detail = client.get(f"/api/workouts/{sid}").json()
    assert len(detail["sets"]) == 2

    fin = client.post(f"/api/workouts/{sid}/finish").json()
    assert fin["ended_at"] is not None

    assert client.delete(f"/api/workouts/sets/{s2['id']}").status_code == 204
    assert len(client.get(f"/api/workouts/{sid}").json()["sets"]) == 1


def test_last_time_and_progression(client):
    bench = _exercise(client)
    s1 = client.post("/api/workouts", json={}).json()["id"]
    client.post(f"/api/workouts/{s1}/sets", json={"exercise_id": bench["id"], "weight": "100", "reps": 5})
    client.post(f"/api/workouts/{s1}/finish")

    s2 = client.post("/api/workouts", json={}).json()["id"]
    last = client.get(f"/api/exercises/{bench['id']}/last", params={"exclude": s2}).json()
    assert len(last) == 1
    assert Decimal(last[0]["weight"]) == Decimal("100")

    client.post(f"/api/workouts/{s2}/sets", json={"exercise_id": bench["id"], "weight": "110", "reps": 3})

    prog = client.get(f"/api/exercises/{bench['id']}/progression").json()
    assert len(prog["points"]) == 2
    assert Decimal(prog["prs"]["best_weight"]) == Decimal("110")
    # best est-1RM = max(epley(100,5)=116.7, epley(110,3)=121.0)
    assert Decimal(prog["prs"]["best_est_1rm"]) == Decimal("121.0")


def test_workouts_isolated_per_user(client, second_client):
    bench = _exercise(client)
    sid = client.post("/api/workouts", json={}).json()["id"]
    client.post(f"/api/workouts/{sid}/sets", json={"exercise_id": bench["id"], "weight": "100", "reps": 5})
    assert second_client.get("/api/workouts").json() == []
    assert second_client.get(f"/api/workouts/{sid}").status_code == 404
