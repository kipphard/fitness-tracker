import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiPatch } from "../api/client";
import type { WorkoutSession, WorkoutSet } from "../api/types";
import { useApi } from "../hooks/useApi";
import { datetimeLocalToIso, isoToDatetimeLocal, num, oneDecimal, parseDecimalInput } from "../lib/format";
import { Modal } from "./Modal";

// Edit a past (finished) workout: fix its start/end time or correct a logged set's
// weight/reps. Set edits reuse the same PATCH endpoint the live session uses.
export function WorkoutEditModal({
  sessionId,
  nameFor,
  onClose,
}: {
  sessionId: string;
  nameFor: (id: string, fallback: string) => string;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const detail = useApi<WorkoutSession>(`/workouts/${sessionId}`);
  const [startLocal, setStartLocal] = useState("");
  const [endLocal, setEndLocal] = useState("");
  const [error, setError] = useState<string | null>(null);

  // Seed the time inputs once the session loads (keyed on id so a refetch after an
  // edit doesn't clobber what the user is typing).
  useEffect(() => {
    if (detail.data) {
      setStartLocal(isoToDatetimeLocal(detail.data.started_at));
      setEndLocal(isoToDatetimeLocal(detail.data.ended_at));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [detail.data?.id]);

  const saveTime = async () => {
    setError(null);
    const body: Record<string, unknown> = {};
    if (startLocal) body.started_at = datetimeLocalToIso(startLocal);
    if (endLocal) body.ended_at = datetimeLocalToIso(endLocal);
    try {
      await apiPatch(`/workouts/${sessionId}`, body);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const editSet = (set: WorkoutSet, key: "weight" | "reps", value: string) => {
    const v = key === "reps" ? value.trim() : parseDecimalInput(value);
    if (v === "") return;
    if (key === "reps" ? Number(v) === set.reps : num(v) === num(set.weight)) return;
    apiPatch(`/workouts/${sessionId}/sets/${set.id}`, {
      [key]: key === "reps" ? Number(v) : v,
    }).catch(() => undefined);
  };
  const deleteSet = (set: WorkoutSet) =>
    apiDelete(`/workouts/sets/${set.id}`).catch(() => undefined);

  const sets = detail.data?.sets ?? [];
  // Group sets by exercise, preserving first-seen order; sets already come ordered by index.
  const groups: { id: string; name: string; sets: WorkoutSet[] }[] = [];
  for (const s of sets) {
    const gid = s.exercise_id ?? s.exercise_name;
    let g = groups.find((x) => x.id === gid);
    if (!g) {
      g = { id: gid, name: nameFor(s.exercise_id ?? "", s.exercise_name), sets: [] };
      groups.push(g);
    }
    g.sets.push(s);
  }

  return (
    <Modal
      title={t("workouts.editTitle")}
      onClose={onClose}
      footer={
        <div className="diary-actions">
          <button className="btn btn--primary" onClick={onClose}>{t("common.done")}</button>
        </div>
      }
    >
      <div className="form__row">
        <label className="field">
          <span>{t("workouts.startTime")}</span>
          <input
            className="input"
            type="datetime-local"
            value={startLocal}
            onChange={(e) => setStartLocal(e.target.value)}
            onBlur={saveTime}
          />
        </label>
        <label className="field">
          <span>{t("workouts.endTime")}</span>
          <input
            className="input"
            type="datetime-local"
            value={endLocal}
            onChange={(e) => setEndLocal(e.target.value)}
            onBlur={saveTime}
          />
        </label>
      </div>
      {error && <div className="error">{error}</div>}

      {groups.length === 0 ? (
        <p className="muted">{t("workouts.noSets")}</p>
      ) : (
        groups.map((g) => (
          <div className="slot-group" key={g.id}>
            <h3>{g.name}</h3>
            <div className="set-table">
              <div className="set-table__head set-table__head--edit">
                <span>{t("workouts.set")}</span>
                <span>{t("workouts.weight")}</span>
                <span>{t("workouts.reps")}</span>
                <span aria-hidden />
              </div>
              {g.sets.map((s, i) => (
                <div key={s.id} className="set-row set-row--edit">
                  <span className="set-row__idx">{s.set_type === "warmup" ? "W" : i + 1}</span>
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
                  <button
                    className="icon-btn icon-btn--xs"
                    onClick={() => deleteSet(s)}
                    aria-label={t("workouts.deleteSet")}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>
          </div>
        ))
      )}
    </Modal>
  );
}
