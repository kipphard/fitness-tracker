import type { Exercise } from "../api/types";

// Public-domain Everkinetic illustrations from free-exercise-db. The API stores a
// relative path (e.g. "Barbell_Squat/0.jpg"); we prefix the jsDelivr CDN here.
// Swapping to a self-hosted origin later is a one-line change (+ the SW cache rule).
const IMG_BASE =
  "https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/";

export function exerciseImageUrl(e: Pick<Exercise, "image_url">): string | null {
  return e.image_url ? IMG_BASE + e.image_url : null;
}

// free-exercise-db ships a start (…/0.jpg) and end (…/1.jpg) frame per exercise; derive the end
// from the start so the detail view can animate the movement (#17). null when there's no pair.
export function endFrameImageUrl(e: Pick<Exercise, "image_url">): string | null {
  const start = exerciseImageUrl(e);
  return start && /\/0\.jpg$/i.test(start) ? start.replace(/\/0\.jpg$/i, "/1.jpg") : null;
}

export function localizedExerciseName(
  e: Pick<Exercise, "name" | "name_de">,
  lang: string,
): string {
  return lang.startsWith("de") && e.name_de ? e.name_de : e.name;
}

// i18n-safe leaf key for a muscle/equipment value ("lower back" -> "lowerback").
export function vocabKey(raw: string): string {
  return raw.toLowerCase().replace(/[^a-z]/g, "");
}

// Fixed vocabularies from free-exercise-db, used for the picker's filter dropdowns.
export const MUSCLE_GROUPS = [
  "abdominals", "abductors", "adductors", "biceps", "calves", "chest", "forearms",
  "glutes", "hamstrings", "lats", "lower back", "middle back", "neck",
  "quadriceps", "shoulders", "traps", "triceps",
];

export const EQUIPMENT_TYPES = [
  "barbell", "dumbbell", "cable", "machine", "body only", "kettlebells", "bands",
  "medicine ball", "exercise ball", "e-z curl bar", "foam roll", "other",
];
