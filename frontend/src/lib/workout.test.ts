import { describe, expect, it } from "vitest";

import type { Routine, WorkoutSession, WorkoutSet } from "../api/types";
import { buildResumeExercises } from "./workout";

const upper = (_id: string, fallback: string) => fallback.toUpperCase();

const set = (exercise_id: string, exercise_name: string): WorkoutSet => ({
  id: `set-${Math.random()}`,
  exercise_id,
  exercise_name,
  set_index: 1,
  weight: "40",
  reps: 10,
  set_type: "working",
  rpe: null,
});

const detail = (
  sets: WorkoutSet[],
  routine_id: string | null = null,
): Pick<WorkoutSession, "sets" | "routine_id"> => ({ sets, routine_id });

const routine = (exercises: Routine["exercises"]): Routine => ({
  id: "r1",
  name: "Push",
  exercises,
});

// Regression cover for GH #11 (resume an in-progress session).
describe("buildResumeExercises", () => {
  it("returns the distinct logged exercises (first-seen order) for an ad-hoc session", () => {
    const result = buildResumeExercises(
      detail([set("b", "Bench"), set("a", "Squat"), set("b", "Bench")]),
      undefined,
      upper,
    );
    expect(result).toEqual([
      { id: "b", name: "BENCH" },
      { id: "a", name: "Squat".toUpperCase() },
    ]);
  });

  it("localizes the name via resolveName", () => {
    const result = buildResumeExercises(detail([set("a", "Squat")]), undefined, upper);
    expect(result[0].name).toBe("SQUAT");
  });

  it("lists routine exercises first with remaining sets (planned minus logged)", () => {
    const r = routine([
      { exercise_id: "a", exercise_name: "Squat", position: 0, planned_sets: 3, planned_reps: 5 },
      { exercise_id: "b", exercise_name: "Bench", position: 1, planned_sets: 3, planned_reps: 8 },
    ]);
    // 2 of squat's 3 sets already logged; bench untouched.
    const result = buildResumeExercises(detail([set("a", "Squat"), set("a", "Squat")], "r1"), r, upper);
    expect(result).toEqual([
      { id: "a", name: "SQUAT", planned_sets: 1, planned_reps: 5 },
      { id: "b", name: "BENCH", planned_sets: 3, planned_reps: 8 },
    ]);
  });

  it("never returns negative remaining sets when more than planned were logged", () => {
    const r = routine([
      { exercise_id: "a", exercise_name: "Squat", position: 0, planned_sets: 2, planned_reps: 5 },
    ]);
    const result = buildResumeExercises(detail([set("a", "Squat"), set("a", "Squat"), set("a", "Squat")], "r1"), r, upper);
    expect(result[0].planned_sets).toBe(0);
  });

  it("appends logged exercises that aren't part of the routine", () => {
    const r = routine([
      { exercise_id: "a", exercise_name: "Squat", position: 0, planned_sets: 3, planned_reps: 5 },
    ]);
    const result = buildResumeExercises(detail([set("a", "Squat"), set("x", "Curl")], "r1"), r, upper);
    expect(result.map((e) => e.id)).toEqual(["a", "x"]);
    expect(result[1]).toEqual({ id: "x", name: "CURL" });
  });
});
