import Model from "react-body-highlighter";

import type { Exercise } from "../api/types";
import { modelSideFor, toMuscleSlugs } from "../lib/muscleMap";

const BODY = "#9aa1ad"; // mid-grey body, visible on the white thumbnail circle
const HIGHLIGHT = "#11936a";

// A circular muscle-highlight thumbnail (#17): a small body diagram with the exercise's primary
// muscles highlighted — consistent and legible where the old free-exercise-db photos were not.
// Falls back to an emoji when the muscles are unknown. Shared by the picker, routine cards, session.
export function ExerciseThumb({
  exercise,
  className = "exercise-thumb",
}: {
  exercise: Pick<Exercise, "primary_muscles"> | null | undefined;
  className?: string;
}) {
  const muscles = toMuscleSlugs(exercise?.primary_muscles);
  if (muscles.length === 0) {
    return (
      <span className={`${className} exercise-thumb--ph`} aria-hidden>
        🏋️
      </span>
    );
  }
  return (
    <span className={`${className} muscle-thumb`} aria-hidden>
      <Model
        type={modelSideFor(exercise?.primary_muscles)}
        data={[{ name: "", muscles }]}
        bodyColor={BODY}
        highlightedColors={[HIGHLIGHT]}
        svgStyle={{ height: "100%", width: "auto" }}
      />
    </span>
  );
}
