import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { apiPut } from "../api/client";
import type { MacroPrefs, Today } from "../api/types";
import { useApi } from "../hooks/useApi";
import { kcal, num, oneDecimal } from "../lib/format";
import { Card } from "./Card";

const MACRO_COLORS = { protein: "#6366f1", carbs: "#f59e0b", fat: "#10b981" };

function pct(part: string, whole: string): number {
  const total = num(whole);
  return total > 0 ? Math.round((num(part) / total) * 100) : 0;
}

export function TodayScreen() {
  const { t } = useTranslation();
  const today = useApi<Today>("/today");
  const prefs = useApi<MacroPrefs>("/macros");

  const [protein, setProtein] = useState("");
  const [fat, setFat] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (prefs.data) {
      setProtein(prefs.data.protein_g_per_kg);
      setFat(prefs.data.fat_g_per_kg);
    }
  }, [prefs.data]);

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

  const { calories, macros } = today.data;
  const donut = [
    { key: "protein", name: t("today.macros.protein"), value: num(macros.protein_kcal), color: MACRO_COLORS.protein },
    { key: "carbs", name: t("today.macros.carbs"), value: num(macros.carbs_kcal), color: MACRO_COLORS.carbs },
    { key: "fat", name: t("today.macros.fat"), value: num(macros.fat_kcal), color: MACRO_COLORS.fat },
  ];

  const macroCards = [
    { key: "protein", g: macros.protein_g, c: macros.protein_kcal, color: MACRO_COLORS.protein },
    { key: "carbs", g: macros.carbs_g, c: macros.carbs_kcal, color: MACRO_COLORS.carbs },
    { key: "fat", g: macros.fat_g, c: macros.fat_kcal, color: MACRO_COLORS.fat },
  ];

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("today.title")}</h1>
        <p className="muted">{t("today.subtitle")}</p>
      </header>

      <div className="grid grid--2">
        <Card title={t("today.targetTitle")}>
          <div className="target-hero">
            <strong className="tnum">{kcal(calories.target)}</strong>
            <span className="muted">{t("profile.results.perDay")}</span>
          </div>
          <div className="result-row">
            <span className="muted">{t("profile.results.maintenance")}</span>
            <span className="tnum">{kcal(calories.maintenance)}</span>
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
          <div className="alert alert--info">{t("today.foodLogSoon")}</div>
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
                <strong className="tnum">{oneDecimal(m.g)} g</strong>
                <span className="muted tnum">
                  {kcal(m.c)} · {pct(m.c, macros.target_kcal)}%
                </span>
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
