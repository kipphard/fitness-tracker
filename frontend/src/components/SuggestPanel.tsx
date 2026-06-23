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

// "Fill remaining calories" (issue #5). Rule-based basket loads on open (free, instant); the
// meal slot is an input (biases picks), with regenerate + per-item swap, plus an optional
// "✨ Smarter suggestions" Claude path when it's configured.
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
  const [busy, setBusy] = useState(false);
  const [aiLoading, setAiLoading] = useState(false);
  const [swapping, setSwapping] = useState<number | null>(null);
  const [showPrefs, setShowPrefs] = useState(false);
  const [preferences, setPreferences] = useState("");

  const load = async (
    mode: "rule" | "ai",
    exclude: string[] = [],
    slotArg: MealSlot = slot,
  ) => {
    const setL = mode === "ai" ? setAiLoading : setLoading;
    setL(true);
    setError(null);
    try {
      const path = mode === "ai" ? "/food/suggest/ai" : "/food/suggest";
      const body: Record<string, unknown> = {
        date,
        tz,
        slot: slotArg,
        exclude_food_ids: exclude,
      };
      if (mode === "ai" && preferences.trim()) body.preferences = preferences.trim();
      setData(await apiPost<SuggestResponse>(path, body));
      setAdded(new Set());
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setL(false);
    }
  };

  useEffect(() => {
    void load("rule");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentIds = (): string[] =>
    (data?.suggestions ?? []).map((s) => s.food_id).filter((x): x is string => !!x);

  const onSlot = (next: MealSlot) => {
    setSlot(next);
    void load(data?.source ?? "rule", [], next);
  };

  const regenerate = () => load(data?.source ?? "rule", currentIds());

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

  const addAll = async () => {
    if (!data) return;
    setBusy(true);
    try {
      for (let i = 0; i < data.suggestions.length; i++) {
        if (!added.has(i)) await addOne(data.suggestions[i], i);
      }
    } finally {
      setBusy(false);
    }
  };

  // Swap one item for an equivalent-size alternative (rule path: deterministic + fast).
  const swap = async (i: number) => {
    if (!data) return;
    setSwapping(i);
    setError(null);
    try {
      const res = await apiPost<SuggestResponse>("/food/suggest", {
        date,
        tz,
        slot,
        exclude_food_ids: currentIds(),
        count: 1,
        target_kcal: data.suggestions[i].kcal,
      });
      if (res.suggestions.length > 0) {
        const next = [...data.suggestions];
        next[i] = res.suggestions[0];
        setData({ ...data, suggestions: next });
        setAdded((prev) => {
          const n = new Set(prev);
          n.delete(i);
          return n;
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSwapping(null);
    }
  };

  const remaining = data ? num(data.remaining_kcal) : 0;
  const filled = data ? data.suggestions.reduce((a, s) => a + num(s.kcal), 0) : 0;
  const allAdded =
    (data?.suggestions.length ?? 0) > 0 && added.size >= (data?.suggestions.length ?? 0);
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
              <div className="suggest-controls">
                <label className="field suggest-slot">
                  <span>{t("diary.slot")}</span>
                  <select
                    className="select"
                    value={slot}
                    onChange={(e) => onSlot(e.target.value as MealSlot)}
                  >
                    {MEAL_SLOTS.map((s) => (
                      <option key={s} value={s}>
                        {t(`diary.slots.${s}`)}
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={regenerate}
                  disabled={loading || aiLoading}
                >
                  ↻ {t("suggest.regenerate")}
                </button>
                <button
                  className="btn btn--primary btn--sm"
                  onClick={addAll}
                  disabled={busy || allAdded}
                >
                  {allAdded ? `✓ ${t("suggest.added")}` : t("suggest.addAll")}
                </button>
              </div>

              <p className="muted suggest-fills">
                {t("suggest.fills", { filled: kcal(filled), remaining: kcal(remaining) })}
              </p>

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
                    <div className="suggest-item__actions">
                      <button
                        className="btn btn--primary btn--sm"
                        onClick={() => addOne(s, i)}
                        disabled={added.has(i)}
                      >
                        {added.has(i) ? `✓ ${t("suggest.added")}` : t("suggest.add")}
                      </button>
                      <button
                        className="btn btn--ghost btn--sm"
                        onClick={() => swap(i)}
                        disabled={swapping === i || added.has(i)}
                      >
                        {swapping === i ? "…" : `↻ ${t("suggest.swap")}`}
                      </button>
                    </div>
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
                  onClick={() => load("ai")}
                  disabled={aiLoading}
                >
                  {aiLoading ? t("suggest.thinking") : `✨ ${t("suggest.smarter")}`}
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
          )}
        </>
      )}
    </Card>
  );
}
