import type { Routine, WorkoutSession } from "../api/types";

export interface ResumeExercise {
  id: string;
  name: string;
  planned_sets?: number;
  planned_reps?: number | null;
}

// Rebuild the exercise list needed to resume an in-progress session (#11). For a routine
// session, list the planned exercises first — each with its *remaining* sets (planned minus
// already-logged), so completed work isn't re-prompted — then append any extra exercises that
// have logged sets but aren't in the routine. For an ad-hoc session, just the logged exercises
// (first-seen order). `resolveName` localizes the canonical exercise name.
export function buildResumeExercises(
  detail: Pick<WorkoutSession, "sets" | "routine_id">,
  routine: Routine | undefined,
  resolveName: (id: string, fallback: string) => string,
): ResumeExercise[] {
  const loggedCount: Record<string, number> = {};
  const seen = new Set<string>();
  const logged: ResumeExercise[] = [];
  for (const s of detail.sets) {
    if (!s.exercise_id) continue;
    loggedCount[s.exercise_id] = (loggedCount[s.exercise_id] ?? 0) + 1;
    if (!seen.has(s.exercise_id)) {
      seen.add(s.exercise_id);
      logged.push({ id: s.exercise_id, name: resolveName(s.exercise_id, s.exercise_name) });
    }
  }

  if (!routine) return logged;

  const plannedIds = new Set(routine.exercises.map((e) => e.exercise_id));
  return [
    ...routine.exercises.map((e) => ({
      id: e.exercise_id,
      name: resolveName(e.exercise_id, e.exercise_name),
      planned_sets: Math.max(0, e.planned_sets - (loggedCount[e.exercise_id] ?? 0)),
      planned_reps: e.planned_reps,
    })),
    ...logged.filter((l) => !plannedIds.has(l.id)),
  ];
}
