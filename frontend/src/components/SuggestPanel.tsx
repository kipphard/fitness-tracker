import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiPost } from "../api/client";
import {
  MEAL_SLOTS,
  type MealSlot,
  type Suggestion,
  type SuggestResponse,
} from "../api/types";
import { kcal, num, oneDecimal } from "../lib/format";
import { Card } from "./Card";

// "Fill remaining calories" (issue #5). Rule-based suggestions load on open (free, instant);
// an optional "✨ Smarter suggestions" button calls the Claude path when it's configured.
export function SuggestPanel({
  date,
  tz,
  defaultSlot,
  onClose,
}: {
  date: string;
  tz: number;
  defaultSlot: MealSlot;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [data, setData] = useState<SuggestResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [slot, setSlot] = useState<MealSlot>(defaultSlot);
  const [added, setAdded] = useState<Set<number>>(new Set());
  const [aiLoading, setAiLoading] = useState(false);
  const [showPrefs, setShowPrefs] = useState(false);
  const [preferences, setPreferences] = useState("");

  const loadRule = async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await apiPost<SuggestResponse>("/food/suggest", { date, tz }));
      setAdded(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadRule();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runAi = async () => {
    setAiLoading(true);
    setError(null);
    try {
      setData(
        await apiPost<SuggestResponse>("/food/suggest/ai", {
          date,
          tz,
          preferences: preferences.trim() || undefined,
        }),
      );
      setAdded(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setAiLoading(false);
    }
  };

  const addOne = async (s: Suggestion, i: number) => {
    setError(null);
    const body: Record<string, unknown> = { date, slot, amount_g: s.amount_g };
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
      setAdded((prev) => new Set(prev).add(i));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const remaining = data ? num(data.remaining_kcal) : 0;
  const gaps = data
    ? ([
        ["protein", num(data.protein_gap_g)],
        ["carbs", num(data.carbs_gap_g)],
        ["fat", num(data.fat_gap_g)],
      ] as const).filter(([, g]) => g > 0.5)
    : [];
  const hasSuggestions = (data?.suggestions.length ?? 0) > 0;

  return (
    <Card
      title={t("suggest.title")}
      action={
        <button className="btn btn--ghost btn--sm" onClick={onClose}>
          {t("diary.cancel")}
        </button>
      }
    >
      {loading && <p className="muted">{t("suggest.loading")}</p>}
      {error && <div className="error">{error}</div>}

      {data && !loading && (
        <>
          <div className="result-row result-row--target">
            <span>{t("suggest.remaining")}</span>
            <strong className="tnum">{kcal(remaining)} kcal</strong>
          </div>
          {gaps.length > 0 && (
            <p className="muted suggest-gaps">
              {t("suggest.stillNeed")}{" "}
              {gaps
                .map(([key, g]) => `${oneDecimal(g)} g ${t(`today.macros.${key}`)}`)
                .join(" · ")}
            </p>
          )}

          {hasSuggestions && (
            <>
              <label className="field suggest-slot">
                <span>{t("diary.slot")}</span>
                <select
                  className="select"
                  value={slot}
                  onChange={(e) => setSlot(e.target.value as MealSlot)}
                >
                  {MEAL_SLOTS.map((s) => (
                    <option key={s} value={s}>
                      {t(`diary.slots.${s}`)}
                    </option>
                  ))}
                </select>
              </label>

              <ul className="list suggest-list">
                {data.suggestions.map((s, i) => (
                  <li key={i} className="suggest-item">
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
                    <button
                      className="btn btn--primary btn--sm suggest-item__add"
                      onClick={() => addOne(s, i)}
                      disabled={added.has(i)}
                    >
                      {added.has(i) ? `✓ ${t("suggest.added")}` : t("suggest.add")}
                    </button>
                  </li>
                ))}
              </ul>
            </>
          )}

          {!hasSuggestions && (
            <p className="muted">
              {remaining < 50 ? t("suggest.onTarget") : t("suggest.noCandidates")}
            </p>
          )}

          {data.notes && data.source === "ai" && <p className="muted">{data.notes}</p>}

          {data.ai_available && (
            <div className="suggest-ai">
              {showPrefs && (
                <textarea
                  className="input"
                  rows={2}
                  placeholder={t("suggest.prefsPlaceholder")}
                  value={preferences}
                  onChange={(e) => setPreferences(e.target.value)}
                />
              )}
              <div className="diary-actions">
                {!showPrefs && (
                  <button
                    className="btn btn--ghost btn--sm"
                    onClick={() => setShowPrefs(true)}
                  >
                    {t("suggest.addPrefs")}
                  </button>
                )}
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={runAi}
                  disabled={aiLoading}
                >
                  {aiLoading ? t("suggest.thinking") : `✨ ${t("suggest.smarter")}`}
                </button>
                {data.source === "ai" && (
                  <button
                    className="btn btn--link btn--sm"
                    onClick={loadRule}
                    disabled={loading}
                  >
                    {t("suggest.backToYours")}
                  </button>
                )}
              </div>
            </div>
          )}
        </>
      )}
    </Card>
  );
}
