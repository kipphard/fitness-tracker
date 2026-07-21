import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { apiPut } from "../api/client";
import type { MacroPrefs, Today, WeighIn } from "../api/types";
import { useApi } from "../hooks/useApi";
import { addDays, kcal, num, oneDecimal, todayIso } from "../lib/format";
import { Card } from "./Card";
import { StepsFromDistance } from "./StepsFromDistance";
import { MacroBars, RingGauge } from "./ui";

// A result row whose explanatory text is tucked behind an ⓘ toggle (declutters
// the dense breakdown — the hint only appears when tapped).
function InfoRow({
  label,
  value,
  hint,
  strong = false,
}: {
  label: ReactNode;
  value: ReactNode;
  hint: string;
  strong?: boolean;
}) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <div className={"result-row" + (strong ? " result-row--divider result-row--target" : "")}>
        <span className={"info-label" + (strong ? "" : " muted")}>
          {label}
          <button
            type="button"
            className="info-btn"
            aria-label="Info"
            aria-expanded={open}
            onClick={() => setOpen((o) => !o)}
          >
            ⓘ
          </button>
        </span>
        {strong ? (
          <strong className="tnum">{value}</strong>
        ) : (
          <span className="tnum">{value}</span>
        )}
      </div>
      {open && <p className="muted result-hint">{hint}</p>}
    </>
  );
}

export function TodayScreen() {
  const { t } = useTranslation();
  const [date, setDate] = useState(todayIso());
  const isToday = date === todayIso();
  // tz = minutes east of UTC, so workout sessions land on the right local day.
  const tz = -new Date().getTimezoneOffset();
  const today = useApi<Today>(`/today?date=${date}&tz=${tz}`);
  const prefs = useApi<MacroPrefs>("/macros");
  const weighIns = useApi<WeighIn[]>("/weight");

  const [protein, setProtein] = useState("");
  const [fat, setFat] = useState("");
  const [saving, setSaving] = useState(false);
  const [stepsInput, setStepsInput] = useState("");
  const [todayWeight, setTodayWeight] = useState("");
  const [loggingWeight, setLoggingWeight] = useState(false);
  const [weightError, setWeightError] = useState<string | null>(null);

  useEffect(() => {
    if (prefs.data) {
      setProtein(prefs.data.protein_g_per_kg);
      setFat(prefs.data.fat_g_per_kg);
    }
  }, [prefs.data]);

  useEffect(() => {
    if (today.data) setStepsInput(String(today.data.steps));
  }, [today.data]);

  const saveSteps = async () => {
    const n = Number(stepsInput);
    if (!Number.isFinite(n) || n < 0) return;
    await apiPut("/steps", { steps: Math.round(n), date }).catch(() => undefined);
  };

  // Add steps derived from a distance (km → steps calculator, #13) on top of today's count.
  const addSteps = (extra: number) => {
    const total = Math.round((Number(stepsInput) || 0) + extra);
    setStepsInput(String(total));
    apiPut("/steps", { steps: total, date }).catch(() => undefined);
  };

  const logWeight = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoggingWeight(true);
    setWeightError(null);
    try {
      // Saving fires "fit-data-changed", so /today and /weight refetch and this prompt
      // disappears — and the calorie target picks up the new weigh-in.
      await apiPut("/weight", { date: todayIso(), weight_kg: todayWeight });
      setTodayWeight("");
    } catch (err) {
      setWeightError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoggingWeight(false);
    }
  };

  const apply = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      await apiPut("/macros", { protein_g_per_kg: protein, fat_g_per_kg: fat });
    } finally {
      setSaving(false);
    }
  };

  if (today.loading && !today.data) {
    return <div className="muted">{t("common.loading")}</div>;
  }
  if (!today.data) {
    // No profile yet (404) — guide the user to set it up.
    return (
      <div className="screen">
        <Card title={t("today.title")}>
          <p className="muted">{t("today.noProfile")}</p>
          <Link className="btn btn--primary" to="/calculator">
            {t("today.setupProfile")}
          </Link>
        </Card>
      </div>
    );
  }

  const { calories, macros, consumed, remaining_kcal, activity_kcal, workout_kcal } =
    today.data;
  // activity_kcal = step burn + workout burn; split them back out for the breakdown rows.
  const stepKcal = num(activity_kcal) - num(workout_kcal);
  const hasWorkout = num(workout_kcal) > 0;
  const weighedToday = (weighIns.data ?? []).some((w) => w.date === todayIso());
  // The deliberate cut/bulk gap your goal targets (maintenance − target), independent of intake.
  const plannedDeficit = num(calories.maintenance) - num(calories.target);
  // Real total expenditure today = sport-free baseline maintenance + today's steps & workouts.
  // This is what the net deficit is measured against (sport counted once, here on top).
  const totalBurn = num(calories.maintenance) + num(activity_kcal);
  // The live deficit so far today: maintenance minus what's been eaten, plus the step burn.
  const netDeficit =
    num(calories.maintenance) - num(consumed.kcal) + num(activity_kcal);
  // ~7700 kcal per kg of body fat (Wishnofsky's 3500 kcal/lb). A first-order estimate —
  // early loss also includes water/glycogen, and the body adapts over time.
  const KCAL_PER_KG = 7700;
  const weeklyChangeKg = (netDeficit * 7) / KCAL_PER_KG;

  // Ring: how full today's eating budget is (eaten vs eaten+remaining). Over when remaining < 0.
  const budget = num(consumed.kcal) + num(remaining_kcal);
  const ringFraction = budget > 0 ? num(consumed.kcal) / budget : 0;
  const overBudget = num(remaining_kcal) < 0;

  const macroBars = [
    { label: t("today.macros.protein"), value: num(consumed.protein_g), max: num(macros.protein_g), unit: "g" },
    { label: t("today.macros.carbs"), value: num(consumed.carbs_g), max: num(macros.carbs_g), unit: "g" },
    { label: t("today.macros.fat"), value: num(consumed.fat_g), max: num(macros.fat_g), unit: "g" },
  ];

  return (
    <div className="screen">
      <header className="screen__head diary-head">
        <h1>{t("today.title")}</h1>
        <div className="date-nav">
          <button className="icon-btn" onClick={() => setDate(addDays(date, -1))} aria-label={t("diary.prev")}>
            ‹
          </button>
          <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
          <button
            className="icon-btn"
            onClick={() => setDate(addDays(date, 1))}
            aria-label={t("diary.next")}
            disabled={isToday}
          >
            ›
          </button>
          <button className="btn btn--ghost btn--sm" onClick={() => setDate(todayIso())} disabled={isToday}>
            {t("diary.todayBtn")}
          </button>
        </div>
      </header>

      {isToday && weighIns.data && !weighedToday && (
        <Card title={t("today.weighInTitle")}>
          <p className="muted today-weigh__prompt">{t("today.weighInPrompt")}</p>
          <form className="form today-weigh" onSubmit={logWeight}>
            <div className="today-weigh__row">
              <input
                className="input"
                type="number"
                step="0.1"
                min="20"
                max="400"
                inputMode="decimal"
                placeholder={t("weight.weight")}
                value={todayWeight}
                onChange={(e) => setTodayWeight(e.target.value)}
                required
              />
              <button className="btn btn--primary" type="submit" disabled={loggingWeight}>
                {loggingWeight ? t("common.saving") : t("today.logWeightBtn")}
              </button>
            </div>
            {weightError && <div className="error">{weightError}</div>}
          </form>
        </Card>
      )}

      <Card title={t("today.overviewTitle")}>
        <div className="today-overview">
          <div className="today-overview__stat">
            <span className="today-overview__num tnum">{kcal(consumed.kcal)}</span>
            <span className="muted">{t("today.eaten")}</span>
          </div>
          <RingGauge
            size={172}
            fraction={ringFraction}
            over={overBudget}
            label={kcal(remaining_kcal)}
            sublabel={t("today.left")}
          />
          <div className="today-overview__stat">
            <span className="today-overview__num tnum">{kcal(activity_kcal)}</span>
            <span className="muted">{t("today.burned")}</span>
          </div>
        </div>
        <MacroBars bars={macroBars} />
      </Card>

      <Card title={t("today.targetTitle")}>
          <div className="result-row">
            <span className="muted">{t("today.maintenance")}</span>
            <span className="tnum">{kcal(calories.maintenance)}</span>
          </div>
          <div className="result-row">
            <span className="muted">{t("today.targetLabel")}</span>
            <span className="tnum">{kcal(calories.target)}</span>
          </div>
          <div className="result-row">
            <span className="muted">{t("today.eaten")}</span>
            <span className="tnum">{kcal(consumed.kcal)}</span>
          </div>
          <div className="result-row">
            <span className="muted">{t("today.steps")}</span>
            <span className="steps-edit">
              <input
                className="input input--steps"
                type="number"
                min="0"
                step="100"
                value={stepsInput}
                onChange={(e) => setStepsInput(e.target.value)}
                onBlur={saveSteps}
              />
              <span className="muted tnum">+{kcal(stepKcal)}</span>
            </span>
          </div>
          <StepsFromDistance onAdd={addSteps} />
          {hasWorkout && (
            <div className="result-row">
              <span className="muted">{t("today.workout")}</span>
              <span className="muted tnum">+{kcal(workout_kcal)}</span>
            </div>
          )}
          <InfoRow
            label={t("today.totalBurn")}
            value={kcal(totalBurn)}
            hint={t("today.totalBurnHint")}
            strong
          />
          <div className="result-row">
            <span className="muted">{t("today.plannedDeficit")}</span>
            <span className="tnum">{kcal(plannedDeficit)}</span>
          </div>
          <InfoRow
            label={t("today.netDeficit")}
            value={kcal(netDeficit)}
            hint={t("today.netDeficitHint")}
          />
          <div className="result-row">
            <span className="muted">
              {weeklyChangeKg >= 0 ? t("today.weeklyLoss") : t("today.weeklyGain")}
            </span>
            <span className="tnum">
              ~
              {Math.abs(weeklyChangeKg).toLocaleString(undefined, {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}{" "}
              {t("today.kgPerWeek")}
            </span>
          </div>
          {calories.below_floor && (
            <div className="alert alert--warn">
              {t("profile.results.floorWarning", { floor: kcal(calories.floor) })}
            </div>
          )}
          <p className="muted results__basis">
            {t("profile.results.weightBasis", { weight: oneDecimal(calories.weight_kg) })} ·{" "}
            {t(`profile.results.source.${calories.weight_source}`)}
          </p>
          <div className="diary-actions">
            <Link className="btn btn--ghost btn--sm" to="/diary">
              {t("today.openDiary")}
            </Link>
          </div>
        </Card>

      <Card title={t("today.adjustTitle")}>
        <form className="form macro-adjust" onSubmit={apply}>
          <div className="form__row">
            <label className="field">
              <span>{t("today.proteinPerKg")}</span>
              <input
                className="input"
                type="number"
                step="0.1"
                min="0.5"
                max="4"
                value={protein}
                onChange={(e) => setProtein(e.target.value)}
                required
              />
              <small className="muted">{t("today.proteinHint")}</small>
            </label>
            <label className="field">
              <span>{t("today.fatPerKg")}</span>
              <input
                className="input"
                type="number"
                step="0.1"
                min="0.3"
                max="3"
                value={fat}
                onChange={(e) => setFat(e.target.value)}
                required
              />
              <small className="muted">{t("today.fatHint")}</small>
            </label>
          </div>
          {!macros.reconciled && (
            <div className="alert alert--warn">
              {t("today.overTarget", { over: kcal(macros.over_kcal) })}
            </div>
          )}
          <button className="btn btn--primary" type="submit" disabled={saving}>
            {saving ? t("common.saving") : t("today.applyMacros")}
          </button>
        </form>
      </Card>
    </div>
  );
}
