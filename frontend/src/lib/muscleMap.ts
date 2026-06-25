import type { Muscle } from "react-body-highlighter";

// free-exercise-db muscle vocabulary → react-body-highlighter slug. (#17)
const SLUG: Record<string, Muscle> = {
  abdominals: "abs",
  abductors: "abductors",
  adductors: "adductor",
  biceps: "biceps",
  calves: "calves",
  chest: "chest",
  forearms: "forearm",
  glutes: "gluteal",
  hamstrings: "hamstring",
  lats: "upper-back",
  "lower back": "lower-back",
  "middle back": "upper-back",
  neck: "neck",
  quadriceps: "quadriceps",
  shoulders: "front-deltoids",
  traps: "trapezius",
  triceps: "triceps",
};

// Slugs that live on the back of the body model.
const POSTERIOR = new Set<Muscle>([
  "trapezius",
  "upper-back",
  "lower-back",
  "back-deltoids",
  "triceps",
  "gluteal",
  "hamstring",
  "calves",
]);

// Map our muscle names to library slugs, de-duped, dropping anything unmapped.
export function toMuscleSlugs(muscles: string[] | null | undefined): Muscle[] {
  const out: Muscle[] = [];
  for (const m of muscles ?? []) {
    const slug = SLUG[m.toLowerCase().trim()];
    if (slug && !out.includes(slug)) out.push(slug);
  }
  return out;
}

// Pick the body side that best shows the primary muscles: posterior if any maps to the back.
export function modelSideFor(primary: string[] | null | undefined): "anterior" | "posterior" {
  return toMuscleSlugs(primary).some((s) => POSTERIOR.has(s)) ? "posterior" : "anterior";
}
