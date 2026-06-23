import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { apiGet, apiPost } from "../api/client";
import type {
  DayPlanResponse,
  PlanMeal,
  PlanScope,
  Settings,
  Suggestion,
} from "../api/types";
import { kcal, num, oneDecimal } from "../lib/format";
import { AiUnavailableNote } from "./AiUnavailableNote";
import { Card } from "./Card";

// "Generate a day's meal plan" (issue #5 §2). Rule-based plan loads on open (free, instant,
// from the user's own foods); the "✨ Smarter plan" path adds store/country-aware realistic
// products via Claude once configured. Scope toggles whole-day ↔ remaining; meals = 3 or 4.
const MEAL_COUNTS = [3, 4];

export function GenerateDayPlanPanel({
  date,
  tz,
  onClose,
}: {
  date: string;
  tz: number;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [data, setData] = useState<DayPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [aiLoading, setAiLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scope, setScope] = useState<PlanScope>("full_day");
  const [meals, setMeals] = useState(4);
  const [added, setAdded] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [preferences, setPreferences] = useState("");
  const [settings, setSettings] = useState<Settings | null>(null);
  const [shoppingAdded, setShoppingAdded] = useState(false);

  const load = async (
    mode: "rule" | "ai",
    scopeArg: PlanScope = scope,
    mealsArg: number = meals,
  ) => {
    const setL = mode === "ai" ? setAiLoading : setLoading;
    setL(true);
    setError(null);
    try {
      const path = mode === "ai" ? "/food/plan/ai" : "/food/plan";
      const body: Record<string, unknown> = { date, tz, scope: scopeArg, meals: mealsArg };
      if (mode === "ai" && preferences.trim()) body.preferences = preferences.trim();
      setData(await apiPost<DayPlanResponse>(path, body));
      setAdded(new Set());
      setShoppingAdded(false);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setL(false);
    }
  };

  useEffect(() => {
    apiGet<Settings>("/settings").then(setSettings).catch(() => undefined);
    void load("rule");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onScope = (next: PlanScope) => {
    setScope(next);
    void load(data?.source ?? "rule", next, meals);
  };
  const onMeals = (next: number) => {
    setMeals(next);
    void load(data?.source ?? "rule", scope, next);
  };

  const addItem = async (meal: PlanMeal, s: Suggestion, key: string) => {
    setError(null);
    const body: Record<string, unknown> = { date, slot: meal.slot, amount_g: s.amount_g };
    if (s.food_id) body.food_id = s.food_id;
    else
      body.food = {
        name: s.name,
        per100_kcal: s.per100_kcal,
        per100_protein_g: s.per100_protein_g,
        per100_fat_g: s.per100_fat_g,
        per100_carbs_g: s.per100_carbs_g,
      };
    try {
      await apiPost("/diary", body);
      setAdded((prev) => new Set(prev).add(key));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const addAll = async () => {
    if (!data) return;
    setBusy(true);
    try {
      for (const meal of data.meals) {
        for (let i = 0; i < meal.suggestions.length; i++) {
          const key = `${meal.slot}-${i}`;
          if (!added.has(key)) await addItem(meal, meal.suggestions[i], key);
        }
      }
    } finally {
      setBusy(false);
    }
  };

  const addToShopping = async () => {
    if (!data) return;
    const items = data.meals.flatMap((m) =>
      m.suggestions.map((s) => ({ name: s.name, food_id: s.food_id, amount_g: s.amount_g })),
    );
    if (items.length === 0) return;
    try {
      await apiPost("/shopping/from-plan", { items });
      setShoppingAdded(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const planContext = settings
    ? [settings.country, settings.store, settings.dietary_preferences].filter(Boolean).join(" · ")
    : "";
  const totalItems = data ? data.meals.reduce((a, m) => a + m.suggestions.length, 0) : 0;
  const allAdded = totalItems > 0 && added.size >= totalItems;

  return (
    <Card
      title={t("plan.title")}
      action={
        <button className="btn btn--ghost btn--sm" onClick={onClose}>
          {t("diary.cancel")}
        </button>
      }
    >
      <div className="suggest-controls">
        <div className="seg">
          {(["full_day", "remaining"] as PlanScope[]).map((sc) => (
            <button
              key={sc}
              className={`btn btn--sm ${scope === sc ? "btn--primary" : "btn--ghost"}`}
              onClick={() => onScope(sc)}
              disabled={loading || aiLoading}
            >
              {t(`plan.scope.${sc}`)}
            </button>
          ))}
        </div>
        <label className="field suggest-slot">
          <span>{t("plan.meals")}</span>
          <select
            className="select"
            value={meals}
            onChange={(e) => onMeals(Number(e.target.value))}
            disabled={loading || aiLoading}
          >
            {MEAL_COUNTS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
        </label>
      </div>

      {loading && <p className="muted">{t("plan.loading")}</p>}
      {error && <div className="error">{error}</div>}

      {data && !loading && (
        <>
          <div className="result-row result-row--target">
            <span>{t(`plan.scope.${data.scope}`)}</span>
            <strong className="tnum">{kcal(data.target_kcal)} kcal</strong>
          </div>
          <p className="muted suggest-fills">
            {t("plan.planned", {
              planned: kcal(data.planned_kcal),
              target: kcal(data.target_kcal),
            })}
          </p>

          {totalItems > 0 && (
            <>
              <div className="diary-actions">
                <button
                  className="btn btn--primary btn--sm"
                  onClick={addAll}
                  disabled={busy || allAdded}
                >
                  {allAdded ? `✓ ${t("suggest.added")}` : t("plan.addAll")}
                </button>
                <button className="btn btn--ghost btn--sm" onClick={addToShopping}>
                  🛒 {t("shopping.addFromPlan")}
                </button>
              </div>
              {shoppingAdded && (
                <p className="muted">
                  {t("shopping.addedToList")}{" "}
                  <Link to="/shopping">{t("shopping.goToList")}</Link>
                </p>
              )}
            </>
          )}

          {data.meals.map((meal) => (
            <div key={meal.slot} className="plan-meal">
              <div className="plan-meal__head">
                <strong>{t(`diary.slots.${meal.slot}`)}</strong>
                <span className="muted tnum">{kcal(meal.kcal)} kcal</span>
              </div>
              {meal.suggestions.length === 0 ? (
                <p className="muted">{t("plan.emptyMeal")}</p>
              ) : (
                <ul className="list suggest-list">
                  {meal.suggestions.map((s, i) => {
                    const key = `${meal.slot}-${i}`;
                    return (
                      <li key={key} className="suggest-item">
                        <div className="suggest-item__main">
                          <span className="suggest-item__name">{s.name}</span>
                          <span className="muted tnum">
                            {oneDecimal(s.amount_g)} g · {kcal(s.kcal)} kcal
                          </span>
                        </div>
                        <div className="add-form__macros suggest-item__macros">
                          <span><strong className="tnum">{oneDecimal(s.protein_g)} g</strong> {t("today.macros.protein")}</span>
                          <span><strong className="tnum">{oneDecimal(s.carbs_g)} g</strong> {t("today.macros.carbs")}</span>
                          <span><strong className="tnum">{oneDecimal(s.fat_g)} g</strong> {t("today.macros.fat")}</span>
                        </div>
                        {s.reason && <p className="muted suggest-item__reason">{s.reason}</p>}
                        <div className="suggest-item__actions">
                          <button
                            className="btn btn--primary btn--sm"
                            onClick={() => addItem(meal, s, key)}
                            disabled={added.has(key)}
                          >
                            {added.has(key) ? `✓ ${t("suggest.added")}` : t("suggest.add")}
                          </button>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          ))}

          {totalItems === 0 && <p className="muted">{t("plan.empty")}</p>}
          {data.notes && data.source === "ai" && <p className="muted">{data.notes}</p>}
          <p className="muted setting-note">{t("plan.disclaimer")}</p>

          {data.ai_available ? (
            <div className="suggest-ai">
              {planContext && (
                <p className="muted">{t("plan.using", { context: planContext })}</p>
              )}
              {showPrefs && (
                <textarea
                  className="input"
                  rows={2}
                  placeholder={t("plan.prefsPlaceholder")}
                  value={preferences}
                  onChange={(e) => setPreferences(e.target.value)}
                />
              )}
              <div className="diary-actions">
                {!showPrefs && (
                  <button className="btn btn--ghost btn--sm" onClick={() => setShowPrefs(true)}>
                    {t("suggest.addPrefs")}
                  </button>
                )}
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => load("ai")}
                  disabled={aiLoading}
                >
                  {aiLoading ? t("plan.thinking") : `✨ ${t("plan.smarter")}`}
                </button>
                {data.source === "ai" && (
                  <button
                    className="btn btn--link btn--sm"
                    onClick={() => load("rule")}
                    disabled={loading}
                  >
                    {t("suggest.backToYours")}
                  </button>
                )}
              </div>
            </div>
          ) : (
            <AiUnavailableNote />
          )}
        </>
      )}
    </Card>
  );
}
