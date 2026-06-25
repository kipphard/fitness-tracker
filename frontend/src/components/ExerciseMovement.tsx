import { useEffect, useState } from "react";

import type { Exercise } from "../api/types";
import { endFrameImageUrl, exerciseImageUrl } from "../lib/exercise";

// Convey the movement by looping the free-exercise-db start/end photos (…/0.jpg ↔ …/1.jpg) in the
// detail view (#17). These are public-domain frames we already reference. Animates only if the
// end frame actually loads; otherwise shows the single start frame, or nothing if there's no image.
export function ExerciseMovement({ exercise }: { exercise: Pick<Exercise, "image_url"> | null }) {
  const first = exercise ? exerciseImageUrl(exercise) : null;
  const second = exercise ? endFrameImageUrl(exercise) : null;
  const [hasSecond, setHasSecond] = useState(false);
  const [frame, setFrame] = useState(0);

  // Preload the end frame; only animate once we know it exists.
  useEffect(() => {
    setHasSecond(false);
    setFrame(0);
    if (!second) return;
    const img = new Image();
    img.onload = () => setHasSecond(true);
    img.src = second;
  }, [second]);

  useEffect(() => {
    if (!hasSecond) return;
    const id = window.setInterval(() => setFrame((f) => (f === 0 ? 1 : 0)), 900);
    return () => window.clearInterval(id);
  }, [hasSecond]);

  if (!first) return null;
  return (
    <img
      className="exercise-hero"
      src={hasSecond && frame === 1 && second ? second : first}
      alt=""
      loading="lazy"
    />
  );
}
