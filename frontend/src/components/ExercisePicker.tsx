import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import type { Exercise } from "../api/types";
import { EQUIPMENT_TYPES, MUSCLE_GROUPS, localizedExerciseName, vocabKey } from "../lib/exercise";
import { ExerciseDetailModal } from "./ExerciseDetailModal";
import { ExerciseThumb } from "./ExerciseThumb";

// How many rows to render at once. Search/filters narrow the ~870-item library;
// this caps the DOM (and lazy image requests) on phones until the user refines.
const MAX_VISIBLE = 80;

export function ExercisePicker({
  exercises,
  onPick,
  onClose,
  excludeIds = [],
}: {
  exercises: Exercise[];
  onPick: (e: Exercise) => void;
  onClose: () => void;
  excludeIds?: string[];
}) {
  const { t, i18n } = useTranslation();
  const [query, setQuery] = useState("");
  const [equipment, setEquipment] = useState("");
  const [muscle, setMuscle] = useState("");
  const [detail, setDetail] = useState<Exercise | null>(null);

  const lang = i18n.language;
  const muscleLabel = (m: string) => t(`exercise.muscles.${vocabKey(m)}`, { defaultValue: m });
  const equipLabel = (e: string) => t(`exercise.equipment.${vocabKey(e)}`, { defaultValue: e });

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    const exclude = new Set(excludeIds);
    return exercises.filter((e) => {
      if (exclude.has(e.id)) return false;
      if (equipment && e.equipment !== equipment) return false;
      if (muscle && !(e.primary_muscles ?? []).includes(muscle)) return false;
      if (q) {
        const hay = `${e.name} ${e.name_de ?? ""}`.toLowerCase();
        if (!hay.includes(q)) return false;
      }
      return true;
    });
  }, [exercises, query, equipment, muscle, excludeIds]);

  const visible = filtered.slice(0, MAX_VISIBLE);

  return (
    <div className="picker">
      <header className="picker__head">
        <button className="btn btn--link" onClick={onClose}>
          {t("diary.cancel")}
        </button>
        <h2>{t("workouts.pickExerciseTitle")}</h2>
        <span className="picker__spacer" />
      </header>

      <div className="picker__filters">
        <input
          className="input"
          type="search"
          autoFocus
          placeholder={t("workouts.searchExercise")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <div className="picker__selects">
          <select className="select" value={equipment} onChange={(e) => setEquipment(e.target.value)}>
            <option value="">{t("workouts.allEquipment")}</option>
            {EQUIPMENT_TYPES.map((eq) => (
              <option key={eq} value={eq}>{equipLabel(eq)}</option>
            ))}
          </select>
          <select className="select" value={muscle} onChange={(e) => setMuscle(e.target.value)}>
            <option value="">{t("workouts.allMuscles")}</option>
            {MUSCLE_GROUPS.map((m) => (
              <option key={m} value={m}>{muscleLabel(m)}</option>
            ))}
          </select>
        </div>
      </div>

      <ul className="picker__list">
        {visible.map((e) => {
          const primary = (e.primary_muscles ?? [])[0];
          return (
            <li key={e.id} className="picker__rowwrap">
              <button className="picker__row" onClick={() => onPick(e)}>
                <ExerciseThumb exercise={e} />
                <span className="picker__row-text">
                  <span className="picker__row-name">{localizedExerciseName(e, lang)}</span>
                  {primary && <span className="picker__row-sub">{muscleLabel(primary)}</span>}
                </span>
              </button>
              <button
                className="icon-btn picker__info"
                onClick={() => setDetail(e)}
                aria-label={t("exercise.details")}
              >
                ⓘ
              </button>
            </li>
          );
        })}
        {filtered.length === 0 && (
          <li className="muted picker__empty">{t("workouts.noExerciseMatch")}</li>
        )}
      </ul>

      {filtered.length > MAX_VISIBLE && (
        <p className="muted picker__more">
          {t("workouts.refineSearch", { shown: MAX_VISIBLE, total: filtered.length })}
        </p>
      )}

      {detail && (
        <ExerciseDetailModal
          exerciseId={detail.id}
          fallbackName={localizedExerciseName(detail, lang)}
          onClose={() => setDetail(null)}
        />
      )}
    </div>
  );
}
