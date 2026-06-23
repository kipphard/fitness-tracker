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
import { ExerciseThumb } from "./ExerciseThumb";
import { LiveSession } from "./LiveSession";
import { RoutineEditModal } from "./RoutineEditModal";

export function WorkoutsScreen() {
  const { t, i18n } = useTranslation();
  const { chart } = useTheme();
  const [active, setActive] = useState<{
    id: string;
    exercises: { id: string; name: string; planned_sets?: number; planned_reps?: number | null }[];
  } | null>(null);

  const routines = useApi<Routine[]>("/routines");
  const history = useApi<WorkoutSummary[]>("/workouts");
  const library = useApi<Exercise[]>("/exercises");

  // null = closed; { routine: null } = create; { routine } = edit.
  const [routineModal, setRoutineModal] = useState<{ routine: Routine | null } | null>(null);

  const [progId, setProgId] = useState("");
  const [prog, setProg] = useState<Progression | null>(null);
  const [pickerProg, setPickerProg] = useState(false);
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

  const libEx = (id: string) => library.data?.find((x) => x.id === id);
  // Routine/session payloads carry only the canonical English name; localize via the library.
  const exName = (id: string, fallback: string) => {
    const e = libEx(id);
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
      exercises: r.exercises.map((e) => ({
        id: e.exercise_id,
        name: exName(e.exercise_id, e.exercise_name),
        planned_sets: e.planned_sets,
        planned_reps: e.planned_reps,
      })),
    });
  };

  const progExercise = (library.data ?? []).find((e) => e.id === progId);
  const progData = (prog?.points ?? []).map((p) => ({ label: shortDate(p.date), est: num(p.est_1rm) }));

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("workouts.title")}</h1>
        <p className="muted">{t("workouts.subtitle")}</p>
      </header>

      <Card title={t("workouts.start")}>
        <button className="btn btn--primary btn--block" onClick={startEmpty}>
          {t("workouts.startEmpty")}
        </button>

        <div className="routines-head">
          <h3>{t("workouts.routinesHead")}</h3>
          <button className="btn btn--ghost btn--sm" onClick={() => setRoutineModal({ routine: null })}>
            + {t("workouts.newRoutine")}
          </button>
        </div>

        {(routines.data ?? []).length === 0 ? (
          <p className="muted">{t("workouts.noRoutines")}</p>
        ) : (
          <div className="routine-cards">
            {(routines.data ?? []).map((r) => (
              <div key={r.id} className="routine-card">
                <div className="routine-card__head">
                  <strong className="routine-card__name">{r.name}</strong>
                  <div className="routine-card__actions">
                    <button className="icon-btn icon-btn--xs" onClick={() => setRoutineModal({ routine: r })} aria-label={t("workouts.editRoutine")}>✎</button>
                    <button
                      className="icon-btn icon-btn--xs"
                      onClick={() => apiDelete(`/routines/${r.id}`).catch(() => undefined)}
                      aria-label={t("workouts.deleteRoutine")}
                    >
                      ✕
                    </button>
                  </div>
                </div>
                <ul className="routine-card__exercises">
                  {r.exercises.length === 0 && <li className="muted">{t("workouts.noExercises")}</li>}
                  {r.exercises.slice(0, 4).map((e) => (
                    <li key={e.exercise_id}>
                      <ExerciseThumb exercise={libEx(e.exercise_id)} className="exercise-thumb exercise-thumb--sm" />
                      <span className="routine-card__ex-name">{exName(e.exercise_id, e.exercise_name)}</span>
                      <span className="muted tnum">
                        {e.planned_sets}×{e.planned_reps ?? "–"}
                      </span>
                    </li>
                  ))}
                  {r.exercises.length > 4 && (
                    <li className="muted routine-card__more">
                      +{r.exercises.length - 4} {t("workouts.moreExercises")}
                    </li>
                  )}
                </ul>
                <button className="btn btn--primary btn--block btn--sm" onClick={() => startRoutine(r)}>
                  {t("workouts.startRoutineFull")}
                </button>
              </div>
            ))}
          </div>
        )}
      </Card>

      <Card title={t("workouts.progression")}>
        <button className="btn btn--ghost btn--add-exercise" onClick={() => setPickerProg(true)}>
          {progExercise ? localizedExerciseName(progExercise, i18n.language) : t("workouts.pickExercise")}
        </button>
        {prog && prog.points.length > 0 ? (
          <>
            {prog.prs && (
              <div className="pr-row">
                <span className="badge">{t("workouts.prWeight")}: {oneDecimal(prog.prs.best_weight)} kg</span>
                <span className="badge">{t("workouts.pr1rm")}: {oneDecimal(prog.prs.best_est_1rm)} kg</span>
              </div>
            )}
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={progData} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
                <CartesianGrid stroke={chart.grid} strokeDasharray="3 3" />
                <XAxis dataKey="label" stroke={chart.axis} fontSize={11} />
                <YAxis stroke={chart.axis} fontSize={11} domain={["auto", "auto"]} />
                <Tooltip />
                <Line type="monotone" dataKey="est" name={t("workouts.est1rm")} stroke={chart.trend} strokeWidth={2} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </>
        ) : (
          <p className="muted">{progId ? t("workouts.noData") : t("workouts.pickToSee")}</p>
        )}
      </Card>

      <Card title={t("workouts.history")}>
        {(history.data ?? []).length ? (
          <ul className="list">
            {(history.data ?? []).map((h) => (
              <li key={h.id} className="diary-entry">
                <span className="diary-entry__name">
                  {shortDate(h.started_at)}
                  {h.routine_name ? ` · ${h.routine_name}` : ""}
                </span>
                <span className="muted tnum">{h.set_count} {t("workouts.setsShort")}</span>
                <span className="tnum">{oneDecimal(h.total_volume)} kg</span>
                <button
                  className="icon-btn icon-btn--xs"
                  onClick={() => apiDelete(`/workouts/${h.id}`).catch(() => undefined)}
                  aria-label={t("workouts.deleteWorkout")}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">{t("workouts.noHistory")}</p>
        )}
      </Card>

      {routineModal && (
        <RoutineEditModal
          routine={routineModal.routine}
          library={library.data ?? []}
          onClose={() => setRoutineModal(null)}
        />
      )}

      {pickerProg && (
        <ExercisePicker
          exercises={library.data ?? []}
          onClose={() => setPickerProg(false)}
          onPick={(ex) => {
            setProgId(ex.id);
            setPickerProg(false);
          }}
        />
      )}
    </div>
  );
}
