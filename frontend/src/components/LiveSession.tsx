import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiGet, apiPatch, apiPost } from "../api/client";
import type { Exercise, WorkoutSession, WorkoutSet } from "../api/types";
import { useApi } from "../hooks/useApi";
import { localizedExerciseName } from "../lib/exercise";
import { num, oneDecimal, parseDecimalInput } from "../lib/format";
import { Card } from "./Card";
import { ExerciseDetailModal } from "./ExerciseDetailModal";
import { ExercisePicker } from "./ExercisePicker";
import { ExerciseThumb } from "./ExerciseThumb";
import { Modal } from "./Modal";

interface ExRef {
  id: string;
  name: string;
  planned_sets?: number;
  planned_reps?: number | null;
}
interface Draft {
  key: string;
  weight: string;
  reps: string;
}

const REST_SECONDS = 90;
let draftSeq = 0;
const newDraft = (weight = "", reps = ""): Draft => ({ key: `d${draftSeq++}`, weight, reps });

function clock(s: number): string {
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  const mm = String(m).padStart(h ? 2 : 1, "0");
  return `${h ? `${h}:` : ""}${mm}:${String(sec).padStart(2, "0")}`;
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
  const [showFinish, setShowFinish] = useState(false);
  const [last, setLast] = useState<Record<string, WorkoutSet[]>>({});
  const [drafts, setDrafts] = useState<Record<string, Draft[]>>(() =>
    Object.fromEntries(
      initialExercises.map((e) => [
        e.id,
        Array.from({ length: Math.max(1, e.planned_sets ?? 1) }, () => newDraft()),
      ]),
    ),
  );
  const [rest, setRest] = useState(0);
  const [now, setNow] = useState(() => Date.now());
  const [detailId, setDetailId] = useState<string | null>(null);

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

  // One-second tick for the duration clock + rest countdown.
  useEffect(() => {
    const id = window.setInterval(() => {
      setNow(Date.now());
      setRest((r) => (r > 0 ? r - 1 : 0));
    }, 1000);
    return () => window.clearInterval(id);
  }, []);

  const libEx = (id: string) => library.find((x) => x.id === id);
  const allSets = detail.data?.sets ?? [];
  const doneSets = (exId: string) =>
    allSets.filter((s) => s.exercise_id === exId).sort((a, b) => a.set_index - b.set_index);

  const totalVolume = allSets.reduce((a, s) => a + num(s.weight) * s.reps, 0);
  const startedMs = detail.data ? new Date(detail.data.started_at).getTime() : now;
  const elapsed = Math.max(0, Math.floor((now - startedMs) / 1000));

  const setDraft = (exId: string, idx: number, key: "weight" | "reps", value: string) =>
    setDrafts((p) => ({
      ...p,
      [exId]: (p[exId] ?? []).map((d, i) => (i === idx ? { ...d, [key]: value } : d)),
    }));
  const addDraft = (exId: string, prefill?: Draft) =>
    setDrafts((p) => ({ ...p, [exId]: [...(p[exId] ?? []), prefill ?? newDraft()] }));
  const removeDraft = (exId: string, idx: number) =>
    setDrafts((p) => ({ ...p, [exId]: (p[exId] ?? []).filter((_, i) => i !== idx) }));

  // Check off a draft → log the set (falling back to last-time values for a quick same-as-before).
  const logDraft = async (ex: ExRef, idx: number, prev?: WorkoutSet) => {
    const d = (drafts[ex.id] ?? [])[idx];
    if (!d) return;
    const weight = parseDecimalInput(d.weight) || (prev ? String(num(prev.weight)) : "");
    const reps = d.reps.trim() || (prev ? String(prev.reps) : "");
    if (weight === "" || reps === "") return;
    await apiPost(`/workouts/${sessionId}/sets`, {
      exercise_id: ex.id,
      weight,
      reps: Number(reps),
    }).catch(() => undefined);
    removeDraft(ex.id, idx);
    setRest(REST_SECONDS);
  };

  const editSet = (set: WorkoutSet, key: "weight" | "reps", value: string) => {
    const v = key === "reps" ? value.trim() : parseDecimalInput(value);
    if (v === "") return;
    if (key === "reps" ? Number(v) === set.reps : num(v) === num(set.weight)) return;
    apiPatch(`/workouts/${sessionId}/sets/${set.id}`, {
      [key]: key === "reps" ? Number(v) : v,
    }).catch(() => undefined);
  };
  const toggleWarmup = (set: WorkoutSet) =>
    apiPatch(`/workouts/${sessionId}/sets/${set.id}`, {
      set_type: set.set_type === "warmup" ? "working" : "warmup",
    }).catch(() => undefined);
  // Uncheck a logged set → delete it, but keep its values as a fresh draft so nothing is lost.
  const uncheck = async (set: WorkoutSet) => {
    await apiDelete(`/workouts/sets/${set.id}`).catch(() => undefined);
    addDraft(set.exercise_id ?? "", newDraft(oneDecimal(set.weight), String(set.reps)));
  };

  const addExercise = (ex: Exercise) => {
    setShowPicker(false);
    if (exercises.some((x) => x.id === ex.id)) return;
    setExercises((p) => [...p, { id: ex.id, name: localizedExerciseName(ex, i18n.language) }]);
    setDrafts((p) => ({ ...p, [ex.id]: [newDraft()] }));
    void fetchLast(ex.id);
  };

  const finish = async () => {
    await apiPost(`/workouts/${sessionId}/finish`, {}).catch(() => undefined);
    onFinish();
  };
  const discard = async () => {
    await apiDelete(`/workouts/${sessionId}`).catch(() => undefined);
    onFinish();
  };

  const stats = useMemo(
    () => [
      { k: "duration", v: clock(elapsed) },
      { k: "volume", v: `${oneDecimal(totalVolume)} kg` },
      { k: "setsCount", v: String(allSets.length) },
    ],
    [elapsed, totalVolume, allSets.length],
  );

  return (
    <div className="screen live-session">
      <header className="screen__head workout-head">
        <div>
          <h1>{t("workouts.active")}</h1>
          <div className="session-stats">
            {stats.map((s) => (
              <span key={s.k}>
                <strong className="tnum">{s.v}</strong> {t(`workouts.${s.k}`)}
              </span>
            ))}
          </div>
        </div>
        <div className="workout-head__actions">
          {rest > 0 && (
            <button className="btn btn--ghost btn--sm rest-timer" onClick={() => setRest(0)}>
              ⏱ {clock(rest)} · {t("workouts.skipRest")}
            </button>
          )}
          <button className="btn btn--primary btn--sm" onClick={() => setShowFinish(true)}>
            {t("workouts.finish")}
          </button>
        </div>
      </header>

      {exercises.map((ex) => {
        const done = doneSets(ex.id);
        const prev = last[ex.id] ?? [];
        const exItems = drafts[ex.id] ?? [];
        return (
          <Card
            key={ex.id}
            title={
              <button className="ex-title ex-title--btn" onClick={() => setDetailId(ex.id)}>
                <ExerciseThumb exercise={libEx(ex.id)} className="exercise-thumb exercise-thumb--sm" />
                {ex.name}
                <span className="ex-title__info" aria-hidden>ⓘ</span>
              </button>
            }
            action={
              ex.planned_sets ? (
                <span className="muted tnum">{done.length}/{ex.planned_sets}</span>
              ) : undefined
            }
          >
            <div className="set-table">
              <div className="set-table__head">
                <span>{t("workouts.set")}</span>
                <span>{t("workouts.previous")}</span>
                <span>{t("workouts.weight")}</span>
                <span>{t("workouts.reps")}</span>
                <span aria-hidden>✓</span>
              </div>

              {done.map((s, i) => (
                <div key={s.id} className="set-row set-row--done">
                  <button
                    className={"set-row__idx" + (s.set_type === "warmup" ? " is-warmup" : "")}
                    onClick={() => toggleWarmup(s)}
                    title={t("workouts.warmupHint")}
                  >
                    {s.set_type === "warmup" ? "W" : i + 1}
                  </button>
                  <span className="set-row__prev muted">
                    {prev[i] ? `${oneDecimal(prev[i].weight)}×${prev[i].reps}` : "–"}
                  </span>
                  <input
                    className="input set-row__num"
                    type="text"
                    inputMode="decimal"
                    defaultValue={oneDecimal(s.weight)}
                    onBlur={(e) => editSet(s, "weight", e.target.value)}
                  />
                  <input
                    className="input set-row__num"
                    type="number"
                    step="1"
                    min="0"
                    defaultValue={String(s.reps)}
                    onBlur={(e) => editSet(s, "reps", e.target.value)}
                  />
                  <button className="set-check is-done" onClick={() => uncheck(s)} aria-label={t("workouts.uncheck")}>
                    ✓
                  </button>
                </div>
              ))}

              {exItems.map((d, idx) => {
                const prevSet = prev[done.length + idx];
                return (
                  <div key={d.key} className="set-row">
                    <span className="set-row__idx is-draft">{done.length + idx + 1}</span>
                    <span className="set-row__prev muted">
                      {prevSet ? `${oneDecimal(prevSet.weight)}×${prevSet.reps}` : "–"}
                    </span>
                    <input
                      className="input set-row__num"
                      type="text"
                      inputMode="decimal"
                      placeholder={prevSet ? oneDecimal(prevSet.weight) : t("workouts.weight")}
                      value={d.weight}
                      onChange={(e) => setDraft(ex.id, idx, "weight", e.target.value)}
                    />
                    <input
                      className="input set-row__num"
                      type="number"
                      step="1"
                      min="0"
                      placeholder={prevSet ? String(prevSet.reps) : (ex.planned_reps ? String(ex.planned_reps) : t("workouts.reps"))}
                      value={d.reps}
                      onChange={(e) => setDraft(ex.id, idx, "reps", e.target.value)}
                    />
                    <button className="set-check" onClick={() => logDraft(ex, idx, prevSet)} aria-label={t("workouts.markDone")}>
                      ✓
                    </button>
                  </div>
                );
              })}
            </div>

            <button className="btn btn--ghost btn--sm btn--block" onClick={() => addDraft(ex.id)}>
              + {t("workouts.addSet")}
            </button>
          </Card>
        );
      })}

      <button className="btn btn--ghost btn--add-exercise btn--block" onClick={() => setShowPicker(true)}>
        + {t("workouts.addExercise")}
      </button>

      {showPicker && (
        <ExercisePicker
          exercises={library}
          excludeIds={exercises.map((x) => x.id)}
          onClose={() => setShowPicker(false)}
          onPick={addExercise}
        />
      )}

      {detailId && (
        <ExerciseDetailModal
          exerciseId={detailId}
          fallbackName={exercises.find((x) => x.id === detailId)?.name}
          onClose={() => setDetailId(null)}
        />
      )}

      {showFinish && (
        <Modal
          title={t("workouts.finishTitle")}
          onClose={() => setShowFinish(false)}
          footer={
            <div className="diary-actions diary-actions--split">
              <button className="btn btn--danger btn--sm" onClick={discard}>{t("workouts.discard")}</button>
              <div className="diary-actions">
                <button className="btn btn--primary" onClick={finish}>{t("workouts.finishWorkout")}</button>
                <button className="btn btn--ghost" onClick={() => setShowFinish(false)}>{t("workouts.keepGoing")}</button>
              </div>
            </div>
          }
        >
          <div className="finish-stats">
            {stats.map((s) => (
              <div key={s.k} className="finish-stats__item">
                <strong className="tnum">{s.v}</strong>
                <span className="muted">{t(`workouts.${s.k}`)}</span>
              </div>
            ))}
          </div>
        </Modal>
      )}
    </div>
  );
}
