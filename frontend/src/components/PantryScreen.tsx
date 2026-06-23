import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiGet, apiPost } from "../api/client";
import type { Food, PantryItem } from "../api/types";
import { useApi } from "../hooks/useApi";
import { kcal } from "../lib/format";
import { Card } from "./Card";

// "What's at home" (issue #5 §2). A simple list of saved foods the suggestion + day-plan
// engines prefer ("use what you have first"). Add by searching your saved foods (or use the
// ⭐ toggle while logging in the Diary); remove with ✕.
export function PantryScreen() {
  const { t } = useTranslation();
  const pantry = useApi<PantryItem[]>("/pantry");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Food[]>([]);
  const [error, setError] = useState<string | null>(null);

  const inPantry = new Set((pantry.data ?? []).map((i) => i.food.id));

  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setResults([]);
      return;
    }
    let active = true;
    apiGet<Food[]>(`/food?q=${encodeURIComponent(q)}`)
      .then((r) => active && setResults(r))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [query]);

  const add = async (food: Food) => {
    setError(null);
    try {
      await apiPost("/pantry", { food_id: food.id });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const remove = async (foodId: string) => {
    setError(null);
    try {
      await apiDelete(`/pantry/${foodId}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const items = pantry.data ?? [];

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>🥫 {t("pantry.title")}</h1>
      </header>

      <Card title={t("pantry.addTitle")}>
        <p className="muted setting-note">{t("pantry.hint")}</p>
        <input
          className="input"
          type="search"
          placeholder={t("pantry.searchPlaceholder")}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        {error && <div className="error">{error}</div>}
        {query.trim().length >= 2 && (
          <ul className="food-results">
            {results.map((f) => (
              <li key={f.id} className="pantry-row">
                <span className="pantry-row__name">{f.name}</span>
                <span className="muted tnum">{kcal(f.per100_kcal)} / 100g</span>
                <button
                  className="btn btn--ghost btn--sm"
                  onClick={() => add(f)}
                  disabled={inPantry.has(f.id)}
                >
                  {inPantry.has(f.id) ? `✓ ${t("pantry.added")}` : t("pantry.add")}
                </button>
              </li>
            ))}
            {results.length === 0 && (
              <li className="muted food-results__empty">{t("diary.noSaved")}</li>
            )}
          </ul>
        )}
      </Card>

      <Card title={t("pantry.listTitle", { count: items.length })}>
        {items.length === 0 ? (
          <p className="muted">{t("pantry.empty")}</p>
        ) : (
          <ul className="food-results">
            {items.map((i) => (
              <li key={i.id} className="pantry-row">
                <span className="pantry-row__name">{i.food.name}</span>
                <span className="muted tnum">{kcal(i.food.per100_kcal)} / 100g</span>
                <button
                  className="icon-btn"
                  onClick={() => remove(i.food.id)}
                  aria-label={t("pantry.remove")}
                  title={t("pantry.remove")}
                >
                  ✕
                </button>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
