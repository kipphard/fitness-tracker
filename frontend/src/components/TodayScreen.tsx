import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { apiPut } from "../api/client";
import type { MacroPrefs, Today, WeighIn } from "../api/types";
import { useApi } from "../hooks/useApi";
import { kcal, num, oneDecimal } from "../lib/format";
import { Card } from "./Card";

const MACRO_COLORS = { protein: "#6366f1", carbs: "#f59e0b", fat: "#10b981" };

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function TodayScreen() {
  const { t } = useTranslation();
  const today = useApi<Today>("/today");
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
    await apiPut("/steps", { steps: Math.round(n) }).catch(() => undefined);
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

  const { calories, macros, consumed, remaining_kcal, activity_kcal } = today.data;
  const weighedToday = (weighIns.data ?? []).some((w) => w.date === todayIso());
  // The deliberate cut/bulk gap your goal targets (maintenance − target), independent of intake.
  const plannedDeficit = num(calories.maintenance) - num(calories.target);
  // The effective deficit for the day: the planned cut plus the extra burn from steps.
  const netDeficit = plannedDeficit + num(activity_kcal);
  // ~7700 kcal per kg of body fat (Wishnofsky's 3500 kcal/lb). A first-order estimate —
  // early loss also includes water/glycogen, and the body adapts over time.
  const KCAL_PER_KG = 7700;
  const weeklyChangeKg = (netDeficit * 7) / KCAL_PER_KG;
  const donut = [
    { key: "protein", name: t("today.macros.protein"), value: num(macros.protein_kcal), color: MACRO_COLORS.protein },
    { key: "carbs", name: t("today.macros.carbs"), value: num(macros.carbs_kcal), color: MACRO_COLORS.carbs },
    { key: "fat", name: t("today.macros.fat"), value: num(macros.fat_kcal), color: MACRO_COLORS.fat },
  ];

  const macroCards = [
    { key: "protein", target: macros.protein_g, eaten: consumed.protein_g, color: MACRO_COLORS.protein },
    { key: "carbs", target: macros.carbs_g, eaten: consumed.carbs_g, color: MACRO_COLORS.carbs },
    { key: "fat", target: macros.fat_g, eaten: consumed.fat_g, color: MACRO_COLORS.fat },
  ];
  const progress = (eaten: string, target: string) => {
    const total = num(target);
    return total > 0 ? Math.min(100, (num(eaten) / total) * 100) : 0;
  };

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("today.title")}</h1>
        <p className="muted">{t("today.subtitle")}</p>
      </header>

      {weighIns.data && !weighedToday && (
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

      <div className="grid grid--2">
        <Card title={t("today.targetTitle")}>
          <div className="target-hero">
            <strong className="tnum">{kcal(remaining_kcal)}</strong>
            <span className="muted">{t("today.left")}</span>
          </div>
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
              <span className="muted tnum">+{kcal(activity_kcal)}</span>
            </span>
          </div>
          <div className="result-row result-row--divider">
            <span className="muted">{t("today.plannedDeficit")}</span>
            <span className="tnum">{kcal(plannedDeficit)}</span>
          </div>
          <div className="result-row">
            <span className="muted">{t("today.netDeficit")}</span>
            <span className="tnum">{kcal(netDeficit)}</span>
          </div>
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
          <p className="muted result-hint">{t("today.netDeficitHint")}</p>
          {calories.below_floor && (
            <div className="alert alert--warn">
              {t("profile.results.floorWarning", { floor: kcal(calories.floor) })}
            </div>
          )}
          <p className="muted results__basis">
            {t("profile.results.weightBasis", { weight: oneDecimal(calories.weight_kg) })} ·{" "}
            {t(`profile.results.source.${calories.weight_source}`)}
          </p>
          <Link className="btn btn--ghost btn--sm" to="/diary">
            {t("today.openDiary")}
          </Link>
        </Card>

        <Card title={t("today.macrosTitle")}>
          <ResponsiveContainer width="100%" height={190}>
            <PieChart>
              <Pie
                data={donut}
                dataKey="value"
                nameKey="name"
                innerRadius={48}
                outerRadius={78}
                paddingAngle={2}
              >
                {donut.map((d) => (
                  <Cell key={d.key} fill={d.color} stroke="none" />
                ))}
              </Pie>
              <Tooltip formatter={(v: number) => `${Math.round(v)} kcal`} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>

          <div className="macro-cards">
            {macroCards.map((m) => (
              <div className="macro-card" key={m.key}>
                <span className="macro-card__dot" style={{ background: m.color }} />
                <span className="macro-card__name">{t(`today.macros.${m.key}`)}</span>
                <strong className="tnum">
                  {oneDecimal(m.eaten)} / {oneDecimal(m.target)} g
                </strong>
                <div className="macro-bar">
                  <div
                    className="macro-bar__fill"
                    style={{ width: `${progress(m.eaten, m.target)}%`, background: m.color }}
                  />
                </div>
              </div>
            ))}
          </div>
        </Card>
      </div>

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
