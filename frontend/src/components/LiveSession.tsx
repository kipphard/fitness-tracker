import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiGet, apiPost } from "../api/client";
import type { Exercise, WorkoutSession, WorkoutSet } from "../api/types";
import { useApi } from "../hooks/useApi";
import { localizedExerciseName } from "../lib/exercise";
import { oneDecimal } from "../lib/format";
import { Card } from "./Card";
import { ExercisePicker } from "./ExercisePicker";

interface ExRef {
  id: string;
  name: string;
}

const REST_SECONDS = 90;

function mmss(s: number): string {
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export function LiveSession({
  sessionId,
  initialExercises,
  onFinish,
}: {
  sessionId: string;
  initialExercises: ExRef[];
  onFinish: () => void;
}) {
  const { t, i18n } = useTranslation();
  const detail = useApi<WorkoutSession>(`/workouts/${sessionId}`);
  const [exercises, setExercises] = useState<ExRef[]>(initialExercises);
  const [library, setLibrary] = useState<Exercise[]>([]);
  const [showPicker, setShowPicker] = useState(false);
  const [last, setLast] = useState<Record<string, WorkoutSet[]>>({});
  const [inputs, setInputs] = useState<Record<string, { weight: string; reps: string }>>({});
  const [rest, setRest] = useState(0);

  useEffect(() => {
    apiGet<Exercise[]>("/exercises").then(setLibrary).catch(() => undefined);
  }, []);

  const fetchLast = (exId: string) =>
    apiGet<WorkoutSet[]>(`/exercises/${exId}/last?exclude=${sessionId}`)
      .then((s) => setLast((p) => ({ ...p, [exId]: s })))
      .catch(() => undefined);

  useEffect(() => {
    initialExercises.forEach((e) => fetchLast(e.id));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Rest countdown: one interval while rest > 0.
  useEffect(() => {
    if (rest <= 0) return;
    const id = window.setInterval(() => setRest((r) => (r <= 1 ? 0 : r - 1)), 1000);
    return () => window.clearInterval(id);
  }, [rest > 0]);

  const setInput = (exId: string, key: "weight" | "reps", value: string) =>
    setInputs((p) => {
      const cur = p[exId] ?? { weight: "", reps: "" };
      return { ...p, [exId]: { ...cur, [key]: value } };
    });

  const logSet = async (ex: ExRef) => {
    const inp = inputs[ex.id] || { weight: "", reps: "" };
    if (!inp.weight || !inp.reps) return;
    await apiPost(`/workouts/${sessionId}/sets`, {
      exercise_id: ex.id,
      weight: inp.weight,
      reps: Number(inp.reps),
    }).catch(() => undefined);
    setRest(REST_SECONDS);
  };

  const addExercise = (ex: Exercise) => {
    setShowPicker(false);
    if (exercises.some((x) => x.id === ex.id)) return;
    setExercises((p) => [...p, { id: ex.id, name: localizedExerciseName(ex, i18n.language) }]);
    void fetchLast(ex.id);
  };

  const finish = async () => {
    await apiPost(`/workouts/${sessionId}/finish`, {}).catch(() => undefined);
    onFinish();
  };

  const setsFor = (exId: string) =>
    (detail.data?.sets ?? []).filter((s) => s.exercise_id === exId);

  return (
    <div className="screen">
      <header className="screen__head workout-head">
        <h1>{t("workouts.active")}</h1>
        <div className="workout-head__actions">
          {rest > 0 && (
            <button className="btn btn--ghost btn--sm rest-timer" onClick={() => setRest(0)}>
              ⏱ {mmss(rest)} · {t("workouts.skipRest")}
            </button>
          )}
          <button className="btn btn--primary btn--sm" onClick={finish}>
            {t("workouts.finish")}
          </button>
        </div>
      </header>

      {exercises.map((ex) => {
        const lastSets = last[ex.id] ?? [];
        const done = setsFor(ex.id);
        const inp = inputs[ex.id] || { weight: "", reps: "" };
        return (
          <Card key={ex.id} title={ex.name}>
            {lastSets.length > 0 && (
              <p className="muted last-time">
                {t("workouts.lastTime")}:{" "}
                {lastSets.map((s) => `${oneDecimal(s.weight)}×${s.reps}`).join(", ")}
              </p>
            )}
            {done.length > 0 && (
              <ul className="list set-list">
                {done.map((s) => (
                  <li key={s.id} className="diary-entry">
                    <span className="diary-entry__name">{t("workouts.set")} {s.set_index}</span>
                    <span className="tnum">{oneDecimal(s.weight)} kg × {s.reps}</span>
                    <button
                      className="icon-btn icon-btn--xs"
                      onClick={() => apiDelete(`/workouts/sets/${s.id}`).catch(() => undefined)}
                      aria-label={t("weight.delete")}
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <div className="set-input">
              <input
                className="input"
                type="number"
                step="0.5"
                min="0"
                placeholder={t("workouts.weight")}
                value={inp.weight}
                onChange={(e) => setInput(ex.id, "weight", e.target.value)}
              />
              <input
                className="input"
                type="number"
                step="1"
                min="0"
                placeholder={t("workouts.reps")}
                value={inp.reps}
                onChange={(e) => setInput(ex.id, "reps", e.target.value)}
              />
              <button className="btn btn--primary btn--sm" onClick={() => logSet(ex)}>
                {t("workouts.addSet")}
              </button>
            </div>
          </Card>
        );
      })}

      <Card title={t("workouts.addExercise")}>
        <button className="btn btn--ghost btn--add-exercise" onClick={() => setShowPicker(true)}>
          + {t("workouts.pickExercise")}
        </button>
      </Card>

      {showPicker && (
        <ExercisePicker
          exercises={library}
          excludeIds={exercises.map((x) => x.id)}
          onClose={() => setShowPicker(false)}
          onPick={addExercise}
        />
      )}
    </div>
  );
}
