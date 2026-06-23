import { useState } from "react";

import type { Exercise } from "../api/types";
import { exerciseImageUrl } from "../lib/exercise";

// A circular exercise illustration (free-exercise-db via CDN) with an emoji fallback when the
// exercise has no image or the request fails. Shared by the picker, routine cards, and session.
export function ExerciseThumb({
  exercise,
  className = "exercise-thumb",
}: {
  exercise: Pick<Exercise, "image_url"> | null | undefined;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);
  const src = exercise ? exerciseImageUrl(exercise) : null;
  if (!src || failed) {
    return <span className={`${className} exercise-thumb--ph`} aria-hidden>🏋️</span>;
  }
  return (
    <img
      className={className}
      src={src}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
    />
  );
}
