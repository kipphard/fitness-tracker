"""A curated starter exercise library (Phase 7).

Common compound + accessory lifts covering a Push/Pull/Legs/Core split, seeded as global
``source=lib`` exercises. (The full free-exercise-db import with images is a later enhancement.)
"""
from __future__ import annotations

LIBRARY_EXERCISES: list[dict] = [
    # Push
    {"name": "Barbell Bench Press", "category": "push", "equipment": "barbell",
     "primary_muscles": ["chest"], "secondary_muscles": ["triceps", "front delts"]},
    {"name": "Incline Dumbbell Press", "category": "push", "equipment": "dumbbell",
     "primary_muscles": ["chest"], "secondary_muscles": ["front delts", "triceps"]},
    {"name": "Overhead Press", "category": "push", "equipment": "barbell",
     "primary_muscles": ["shoulders"], "secondary_muscles": ["triceps"]},
    {"name": "Dumbbell Shoulder Press", "category": "push", "equipment": "dumbbell",
     "primary_muscles": ["shoulders"], "secondary_muscles": ["triceps"]},
    {"name": "Lateral Raise", "category": "push", "equipment": "dumbbell",
     "primary_muscles": ["side delts"], "secondary_muscles": []},
    {"name": "Triceps Pushdown", "category": "push", "equipment": "cable",
     "primary_muscles": ["triceps"], "secondary_muscles": []},
    # Pull
    {"name": "Deadlift", "category": "pull", "equipment": "barbell",
     "primary_muscles": ["back", "hamstrings"], "secondary_muscles": ["glutes", "forearms"]},
    {"name": "Barbell Row", "category": "pull", "equipment": "barbell",
     "primary_muscles": ["back"], "secondary_muscles": ["biceps", "rear delts"]},
    {"name": "Lat Pulldown", "category": "pull", "equipment": "cable",
     "primary_muscles": ["lats"], "secondary_muscles": ["biceps"]},
    {"name": "Pull-Up", "category": "pull", "equipment": "bodyweight",
     "primary_muscles": ["lats"], "secondary_muscles": ["biceps"]},
    {"name": "Seated Cable Row", "category": "pull", "equipment": "cable",
     "primary_muscles": ["back"], "secondary_muscles": ["biceps"]},
    {"name": "Face Pull", "category": "pull", "equipment": "cable",
     "primary_muscles": ["rear delts"], "secondary_muscles": ["traps"]},
    {"name": "Barbell Curl", "category": "pull", "equipment": "barbell",
     "primary_muscles": ["biceps"], "secondary_muscles": ["forearms"]},
    {"name": "Hammer Curl", "category": "pull", "equipment": "dumbbell",
     "primary_muscles": ["biceps", "forearms"], "secondary_muscles": []},
    # Legs
    {"name": "Barbell Back Squat", "category": "legs", "equipment": "barbell",
     "primary_muscles": ["quads", "glutes"], "secondary_muscles": ["hamstrings", "core"]},
    {"name": "Romanian Deadlift", "category": "legs", "equipment": "barbell",
     "primary_muscles": ["hamstrings", "glutes"], "secondary_muscles": ["back"]},
    {"name": "Leg Press", "category": "legs", "equipment": "machine",
     "primary_muscles": ["quads", "glutes"], "secondary_muscles": ["hamstrings"]},
    {"name": "Leg Curl", "category": "legs", "equipment": "machine",
     "primary_muscles": ["hamstrings"], "secondary_muscles": []},
    {"name": "Leg Extension", "category": "legs", "equipment": "machine",
     "primary_muscles": ["quads"], "secondary_muscles": []},
    {"name": "Walking Lunge", "category": "legs", "equipment": "dumbbell",
     "primary_muscles": ["quads", "glutes"], "secondary_muscles": ["hamstrings"]},
    {"name": "Standing Calf Raise", "category": "legs", "equipment": "machine",
     "primary_muscles": ["calves"], "secondary_muscles": []},
    # Core
    {"name": "Plank", "category": "core", "equipment": "bodyweight",
     "primary_muscles": ["core"], "secondary_muscles": []},
    {"name": "Hanging Leg Raise", "category": "core", "equipment": "bodyweight",
     "primary_muscles": ["core"], "secondary_muscles": ["hip flexors"]},
]
