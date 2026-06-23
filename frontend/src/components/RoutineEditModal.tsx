import { useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiPost, apiPut } from "../api/client";
import type { Exercise, Routine } from "../api/types";
import { localizedExerciseName } from "../lib/exercise";
import { ExercisePicker } from "./ExercisePicker";
import { ExerciseThumb } from "./ExerciseThumb";
import { Modal } from "./Modal";

interface Item {
  exercise_id: string;
  name: string;
  image_url: string | null;
  planned_sets: number;
  planned_reps: number | null;
}

// Create or edit a routine (issue: routines weren't editable). Rename, add/remove/reorder
// exercises, set planned sets×reps. Saves via POST /routines (create) or PUT /routines/{id}.
export function RoutineEditModal({
  routine,
  library,
  onClose,
}: {
  routine: Routine | null;
  library: Exercise[];
  onClose: () => void;
}) {
  const { t, i18n } = useTranslation();
  const byId = (id: string) => library.find((e) => e.id === id);

  const [name, setName] = useState(routine?.name ?? "");
  const [items, setItems] = useState<Item[]>(
    (routine?.exercises ?? []).map((re) => {
      const ex = byId(re.exercise_id);
      return {
        exercise_id: re.exercise_id,
        name: ex ? localizedExerciseName(ex, i18n.language) : re.exercise_name,
        image_url: ex?.image_url ?? null,
        planned_sets: re.planned_sets,
        planned_reps: re.planned_reps,
      };
    }),
  );
  const [pickerOpen, setPickerOpen] = useState(false);
  const [busy, setBusy] = useState(false);

  const addItem = (ex: Exercise) => {
    setPickerOpen(false);
    if (items.some((i) => i.exercise_id === ex.id)) return;
    setItems((p) => [
      ...p,
      {
        exercise_id: ex.id,
        name: localizedExerciseName(ex, i18n.language),
        image_url: ex.image_url,
        planned_sets: 3,
        planned_reps: null,
      },
    ]);
  };
  const patch = (id: string, fields: Partial<Item>) =>
    setItems((p) => p.map((x) => (x.exercise_id === id ? { ...x, ...fields } : x)));
  const remove = (id: string) => setItems((p) => p.filter((x) => x.exercise_id !== id));
  const move = (idx: number, dir: -1 | 1) =>
    setItems((p) => {
      const next = [...p];
      const j = idx + dir;
      if (j < 0 || j >= next.length) return p;
      [next[idx], next[j]] = [next[j], next[idx]];
      return next;
    });

  const save = async () => {
    if (!name.trim() || items.length === 0) return;
    setBusy(true);
    const body = {
      name: name.trim(),
      exercises: items.map((i) => ({
        exercise_id: i.exercise_id,
        planned_sets: i.planned_sets,
        planned_reps: i.planned_reps,
      })),
    };
    try {
      if (routine) await apiPut(`/routines/${routine.id}`, body);
      else await apiPost("/routines", body);
      onClose();
    } finally {
      setBusy(false);
    }
  };

  const del = async () => {
    if (!routine) return;
    setBusy(true);
    try {
      await apiDelete(`/routines/${routine.id}`);
      onClose();
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <Modal
        title={routine ? t("workouts.editRoutine") : t("workouts.newRoutine")}
        onClose={onClose}
        footer={
          <div className="diary-actions diary-actions--split">
            {routine ? (
              <button className="btn btn--danger btn--sm" onClick={del} disabled={busy}>
                {t("workouts.deleteRoutine")}
              </button>
            ) : (
              <span />
            )}
            <div className="diary-actions">
              <button
                className="btn btn--primary"
                onClick={save}
                disabled={busy || !name.trim() || items.length === 0}
              >
                {t("common.save")}
              </button>
              <button className="btn btn--ghost" onClick={onClose}>{t("diary.cancel")}</button>
            </div>
          </div>
        }
      >
        <input
          className="input"
          placeholder={t("workouts.routineName")}
          value={name}
          autoFocus
          onChange={(e) => setName(e.target.value)}
        />

        {items.length === 0 ? (
          <p className="muted">{t("workouts.emptyRoutineHint")}</p>
        ) : (
          <ul className="routine-edit-list">
            {items.map((i, idx) => (
              <li key={i.exercise_id} className="routine-edit-item">
                <ExerciseThumb exercise={i} />
                <div className="routine-edit-item__main">
                  <span className="routine-edit-item__name">{i.name}</span>
                  <div className="routine-edit-item__fields">
                    <label className="micro-field">
                      <span>{t("workouts.sets")}</span>
                      <input
                        className="input input--steps"
                        type="number"
                        min="1"
                        max="20"
                        value={i.planned_sets}
                        onChange={(e) => patch(i.exercise_id, { planned_sets: Number(e.target.value) })}
                      />
                    </label>
                    <label className="micro-field">
                      <span>{t("workouts.reps")}</span>
                      <input
                        className="input input--steps"
                        type="number"
                        min="1"
                        max="100"
                        placeholder="–"
                        value={i.planned_reps ?? ""}
                        onChange={(e) =>
                          patch(i.exercise_id, {
                            planned_reps: e.target.value ? Number(e.target.value) : null,
                          })
                        }
                      />
                    </label>
                  </div>
                </div>
                <div className="routine-edit-item__order">
                  <button className="icon-btn icon-btn--xs" onClick={() => move(idx, -1)} disabled={idx === 0} aria-label="up">↑</button>
                  <button className="icon-btn icon-btn--xs" onClick={() => move(idx, 1)} disabled={idx === items.length - 1} aria-label="down">↓</button>
                  <button className="icon-btn icon-btn--xs" onClick={() => remove(i.exercise_id)} aria-label={t("workouts.deleteRoutine")}>✕</button>
                </div>
              </li>
            ))}
          </ul>
        )}

        <button className="btn btn--ghost btn--add-exercise" onClick={() => setPickerOpen(true)}>
          + {t("workouts.pickExercise")}
        </button>
      </Modal>

      {pickerOpen && (
        <ExercisePicker
          exercises={library}
          excludeIds={items.map((i) => i.exercise_id)}
          onClose={() => setPickerOpen(false)}
          onPick={addItem}
        />
      )}
    </>
  );
}
