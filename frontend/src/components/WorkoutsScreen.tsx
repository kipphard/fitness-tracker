import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { apiDelete, apiGet, apiPost } from "../api/client";
import type { Exercise, Progression, Routine, WorkoutSummary } from "../api/types";
import { useApi } from "../hooks/useApi";
import { localizedExerciseName } from "../lib/exercise";
import { num, oneDecimal, shortDate } from "../lib/format";
import { useTheme } from "../theme";
import { Card } from "./Card";
import { ExercisePicker } from "./ExercisePicker";
import { LiveSession } from "./LiveSession";

interface BuilderItem {
  exercise_id: string;
  name: string;
  planned_sets: number;
}

export function WorkoutsScreen() {
  const { t, i18n } = useTranslation();
  const { chart } = useTheme();
  const [active, setActive] = useState<{ id: string; exercises: { id: string; name: string }[] } | null>(null);

  const routines = useApi<Routine[]>("/routines");
  const history = useApi<WorkoutSummary[]>("/workouts");
  const library = useApi<Exercise[]>("/exercises");

  const [name, setName] = useState("");
  const [items, setItems] = useState<BuilderItem[]>([]);
  const [picker, setPicker] = useState<"routine" | "progression" | null>(null);

  const [progId, setProgId] = useState("");
  const [prog, setProg] = useState<Progression | null>(null);
  useEffect(() => {
    if (!progId) {
      setProg(null);
      return;
    }
    apiGet<Progression>(`/exercises/${progId}/progression`)
      .then(setProg)
      .catch(() => setProg(null));
  }, [progId]);

  if (active) {
    return (
      <LiveSession
        sessionId={active.id}
        initialExercises={active.exercises}
        onFinish={() => setActive(null)}
      />
    );
  }

  // Library entries carry the German name; routine/session payloads only carry the
  // canonical English name, so localize by exercise id where we have the library.
  const exName = (id: string, fallback: string) => {
    const e = library.data?.find((x) => x.id === id);
    return e ? localizedExerciseName(e, i18n.language) : fallback;
  };

  const startEmpty = async () => {
    const s = await apiPost<{ id: string }>("/workouts", {});
    setActive({ id: s.id, exercises: [] });
  };
  const startRoutine = async (r: Routine) => {
    const s = await apiPost<{ id: string }>("/workouts", { routine_id: r.id });
    setActive({
      id: s.id,
      exercises: r.exercises.map((e) => ({ id: e.exercise_id, name: exName(e.exercise_id, e.exercise_name) })),
    });
  };

  const addItem = (ex: Exercise) => {
    if (items.some((i) => i.exercise_id === ex.id)) return;
    setItems((p) => [
      ...p,
      { exercise_id: ex.id, name: localizedExerciseName(ex, i18n.language), planned_sets: 3 },
    ]);
  };
  const createRoutine = async () => {
    if (!name.trim() || items.length === 0) return;
    await apiPost("/routines", {
      name: name.trim(),
      exercises: items.map((i) => ({ exercise_id: i.exercise_id, planned_sets: i.planned_sets })),
    }).catch(() => undefined);
    setName("");
    setItems([]);
  };

  const progExercise = (library.data ?? []).find((e) => e.id === progId);
  const progData = (prog?.points ?? []).map((p) => ({
    label: shortDate(p.date),
    est: num(p.est_1rm),
  }));

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("workouts.title")}</h1>
        <p className="muted">{t("workouts.subtitle")}</p>
      </header>

      <Card title={t("workouts.start")}>
        <button className="btn btn--primary" onClick={startEmpty}>
          {t("workouts.startEmpty")}
        </button>
        {(routines.data ?? []).length > 0 && (
          <ul className="list routine-list">
            {(routines.data ?? []).map((r) => (
              <li key={r.id} className="routine-item">
                <div className="routine-item__info">
                  <strong>{r.name}</strong>
                  <span className="muted">
                    {" "}
                    · {r.exercises.map((e) => exName(e.exercise_id, e.exercise_name)).join(", ") || t("workouts.noExercises")}
                  </span>
                </div>
                <div className="routine-item__actions">
                  <button className="btn btn--ghost btn--sm" onClick={() => startRoutine(r)}>
                    {t("workouts.startRoutine")}
                  </button>
                  <button
                    className="icon-btn icon-btn--xs"
                    onClick={() => apiDelete(`/routines/${r.id}`).catch(() => undefined)}
                    aria-label={t("weight.delete")}
                  >
                    ✕
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <div className="grid grid--2">
        <Card title={t("workouts.newRoutine")}>
          <input
            className="input"
            placeholder={t("workouts.routineName")}
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          {items.length > 0 && (
            <ul className="list">
              {items.map((i) => (
                <li key={i.exercise_id} className="diary-entry">
                  <span className="diary-entry__name">{i.name}</span>
                  <input
                    className="input input--steps"
                    type="number"
                    min="1"
                    max="20"
                    value={i.planned_sets}
                    onChange={(e) =>
                      setItems((p) =>
                        p.map((x) =>
                          x.exercise_id === i.exercise_id
                            ? { ...x, planned_sets: Number(e.target.value) }
                            : x,
                        ),
                      )
                    }
                  />
                  <span className="muted">{t("workouts.sets")}</span>
                  <button
                    className="icon-btn icon-btn--xs"
                    onClick={() => setItems((p) => p.filter((x) => x.exercise_id !== i.exercise_id))}
                    aria-label={t("weight.delete")}
                  >
                    ✕
                  </button>
                </li>
              ))}
            </ul>
          )}
          <button className="btn btn--ghost btn--add-exercise" onClick={() => setPicker("routine")}>
            + {t("workouts.pickExercise")}
          </button>
          <button
            className="btn btn--primary"
            onClick={createRoutine}
            disabled={!name.trim() || items.length === 0}
          >
            {t("workouts.createRoutine")}
          </button>
        </Card>

        <Card title={t("workouts.progression")}>
          <button className="btn btn--ghost btn--add-exercise" onClick={() => setPicker("progression")}>
            {progExercise ? localizedExerciseName(progExercise, i18n.language) : t("workouts.pickExercise")}
          </button>
          {prog && prog.points.length > 0 ? (
            <>
              {prog.prs && (
                <div className="pr-row">
                  <span className="badge">
                    {t("workouts.prWeight")}: {oneDecimal(prog.prs.best_weight)} kg
                  </span>
                  <span className="badge">
                    {t("workouts.pr1rm")}: {oneDecimal(prog.prs.best_est_1rm)} kg
                  </span>
                </div>
              )}
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={progData} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                  <XAxis dataKey="label" stroke={chart.axis} fontSize={11} />
                  <YAxis stroke={chart.axis} fontSize={11} domain={["auto", "auto"]} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="est"
                    name={t("workouts.est1rm")}
                    stroke={chart.trend}
                    strokeWidth={2}
                    dot={{ r: 3 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </>
          ) : (
            <p className="muted">{progId ? t("workouts.noData") : t("workouts.pickToSee")}</p>
          )}
        </Card>
      </div>

      <Card title={t("workouts.history")}>
        {(history.data ?? []).length ? (
          <ul className="list">
            {(history.data ?? []).map((h) => (
              <li key={h.id} className="diary-entry">
                <span className="diary-entry__name">
                  {shortDate(h.started_at)}
                  {h.routine_name ? ` · ${h.routine_name}` : ""}
                </span>
                <span className="muted tnum">
                  {h.set_count} {t("workouts.setsShort")}
                </span>
                <span className="tnum">{oneDecimal(h.total_volume)} kg</span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{t("workouts.noHistory")}</p>
        )}
      </Card>

      {picker && (
        <ExercisePicker
          exercises={library.data ?? []}
          excludeIds={picker === "routine" ? items.map((i) => i.exercise_id) : []}
          onClose={() => setPicker(null)}
          onPick={(ex) => {
            if (picker === "routine") addItem(ex);
            else setProgId(ex.id);
            setPicker(null);
          }}
        />
      )}
    </div>
  );
}
