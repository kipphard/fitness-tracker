import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiGet } from "../api/client";
import type { Exercise } from "../api/types";
import { exerciseImageUrl, localizedExerciseName, vocabKey } from "../lib/exercise";
import { Modal } from "./Modal";
import { MuscleChips } from "./MuscleChips";

// Tap an exercise → its illustration, equipment, target muscles, and instructions. The list
// endpoint omits instructions, so this fetches the full record via GET /exercises/{id}.
export function ExerciseDetailModal({
  exerciseId,
  fallbackName,
  onClose,
}: {
  exerciseId: string;
  fallbackName?: string;
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const [ex, setEx] = useState<Exercise | null>(null);

  useEffect(() => {
    let active = true;
    apiGet<Exercise>(`/exercises/${exerciseId}`)
      .then((e) => active && setEx(e))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [exerciseId]);

  const name = ex ? localizedExerciseName(ex, i18n.language) : fallbackName ?? "";
  const img = ex ? exerciseImageUrl(ex) : null;
  const steps = (ex?.instructions ?? "")
    .split(/\n+/)
    .map((s) => s.trim())
    .filter(Boolean);

  return (
    <Modal title={name} onClose={onClose}>
      {img && <img className="exercise-hero" src={img} alt="" loading="lazy" />}
      {ex?.equipment && (
        <p className="muted">
          {t(`exercise.equipment.${vocabKey(ex.equipment)}`, { defaultValue: ex.equipment })}
        </p>
      )}
      {(ex?.primary_muscles?.length ?? 0) > 0 && (
        <div className="detail-section">
          <span className="detail-label">{t("exercise.primaryMuscles")}</span>
          <MuscleChips muscles={ex?.primary_muscles} />
        </div>
      )}
      {(ex?.secondary_muscles?.length ?? 0) > 0 && (
        <div className="detail-section">
          <span className="detail-label">{t("exercise.secondaryMuscles")}</span>
          <MuscleChips muscles={ex?.secondary_muscles} />
        </div>
      )}
      {steps.length > 0 && (
        <div className="detail-section">
          <span className="detail-label">{t("exercise.instructions")}</span>
          <ol className="exercise-steps">
            {steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
        </div>
      )}
      {!ex && <p className="muted">{t("common.loading")}</p>}
    </Modal>
  );
}
