import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiGet, apiPatch, apiPost } from "../api/client";
import {
  MEAL_SLOTS,
  type DiaryDay,
  type DiaryEntry,
  type Food,
  type FoodData,
  type MealSlot,
} from "../api/types";
import { useApi } from "../hooks/useApi";
import { kcal, oneDecimal } from "../lib/format";
import { Card } from "./Card";

interface Selectable {
  id?: string;
  name: string;
  per100_kcal: string;
  per100_protein_g: string;
  per100_fat_g: string;
  per100_carbs_g: string;
  barcode?: string | null;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}
function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00");
  d.setDate(d.getDate() + n);
  return d.toISOString().slice(0, 10);
}
function toSelectable(f: Food | FoodData): Selectable {
  return {
    id: "id" in f ? f.id : undefined,
    name: f.name,
    per100_kcal: f.per100_kcal,
    per100_protein_g: f.per100_protein_g,
    per100_fat_g: f.per100_fat_g,
    per100_carbs_g: f.per100_carbs_g,
    barcode: f.barcode,
  };
}

export function DiaryScreen() {
  const { t } = useTranslation();
  const [date, setDate] = useState(todayIso());
  const day = useApi<DiaryDay>(`/diary?date=${date}`);
  const recent = useApi<Food[]>("/diary/recent");

  const [query, setQuery] = useState("");
  const [saved, setSaved] = useState<Food[]>([]);
  const [off, setOff] = useState<FoodData[] | null>(null);
  const [offLoading, setOffLoading] = useState(false);
  const [barcode, setBarcode] = useState("");
  const [error, setError] = useState<string | null>(null);

  const [showCustom, setShowCustom] = useState(false);
  const [custom, setCustom] = useState({ name: "", kcal: "", protein: "", fat: "", carbs: "" });

  const [selected, setSelected] = useState<Selectable | null>(null);
  const [amount, setAmount] = useState("100");
  const [slot, setSlot] = useState<MealSlot>("breakfast");

  // Search the user's saved foods as they type.
  useEffect(() => {
    const q = query.trim();
    if (q.length < 2) {
      setSaved([]);
      return;
    }
    let active = true;
    apiGet<Food[]>(`/food?q=${encodeURIComponent(q)}`)
      .then((r) => active && setSaved(r))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [query]);

  const searchOff = async () => {
    const q = query.trim();
    if (q.length < 2) return;
    setOffLoading(true);
    setError(null);
    try {
      setOff(await apiGet<FoodData[]>(`/food/search?q=${encodeURIComponent(q)}`));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setOffLoading(false);
    }
  };

  const lookupBarcode = async () => {
    const code = barcode.trim();
    if (!code) return;
    setError(null);
    try {
      setSelected(toSelectable(await apiGet<Food>(`/food/barcode/${encodeURIComponent(code)}`)));
      setBarcode("");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const useCustom = () => {
    if (!custom.name.trim() || !custom.kcal) return;
    setSelected({
      name: custom.name.trim(),
      per100_kcal: custom.kcal,
      per100_protein_g: custom.protein || "0",
      per100_fat_g: custom.fat || "0",
      per100_carbs_g: custom.carbs || "0",
    });
    setShowCustom(false);
    setCustom({ name: "", kcal: "", protein: "", fat: "", carbs: "" });
  };

  const logSelected = async () => {
    if (!selected) return;
    setError(null);
    const body: Record<string, unknown> = { date, slot, amount_g: amount };
    if (selected.id) body.food_id = selected.id;
    else
      body.food = {
        name: selected.name,
        per100_kcal: selected.per100_kcal,
        per100_protein_g: selected.per100_protein_g,
        per100_fat_g: selected.per100_fat_g,
        per100_carbs_g: selected.per100_carbs_g,
        barcode: selected.barcode ?? null,
      };
    try {
      await apiPost("/diary", body);
      setSelected(null);
      setAmount("100");
      setQuery("");
      setOff(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const editEntry = async (entry: DiaryEntry) => {
    const value = window.prompt(t("diary.editAmount"), entry.amount_g);
    if (value == null) return;
    const n = Number(value);
    if (!Number.isFinite(n) || n <= 0) return;
    await apiPatch(`/diary/${entry.id}`, { amount_g: String(n) }).catch(() => undefined);
  };

  const removeEntry = (id: string) => apiDelete(`/diary/${id}`).catch(() => undefined);
  const copyYesterday = () =>
    apiPost("/diary/copy", { from_date: addDays(date, -1), to_date: date }).catch(() => undefined);

  const results = query.trim().length >= 2 ? saved : recent.data ?? [];
  const totals = day.data?.totals;

  return (
    <div className="screen">
      <header className="screen__head diary-head">
        <h1>{t("diary.title")}</h1>
        <div className="date-nav">
          <button className="icon-btn" onClick={() => setDate(addDays(date, -1))} aria-label={t("diary.prev")}>
            ‹
          </button>
          <input className="input" type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} />
          <button
            className="icon-btn"
            onClick={() => setDate(addDays(date, 1))}
            aria-label={t("diary.next")}
            disabled={date >= todayIso()}
          >
            ›
          </button>
          <button className="btn btn--ghost btn--sm" onClick={() => setDate(todayIso())}>
            {t("diary.todayBtn")}
          </button>
        </div>
      </header>

      <div className="grid grid--2">
        <Card title={t("diary.addTitle")}>
          <input
            className="input"
            type="search"
            placeholder={t("diary.searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />

          <ul className="food-results">
            {results.map((f) => (
              <li key={f.id}>
                <button className="food-results__item" onClick={() => setSelected(toSelectable(f))}>
                  <span>{f.name}</span>
                  <span className="muted tnum">{kcal(f.per100_kcal)} / 100g</span>
                </button>
              </li>
            ))}
            {(off ?? []).map((f, i) => (
              <li key={`off-${i}`}>
                <button className="food-results__item" onClick={() => setSelected(toSelectable(f))}>
                  <span>{f.name} <span className="badge">OFF</span></span>
                  <span className="muted tnum">{kcal(f.per100_kcal)} / 100g</span>
                </button>
              </li>
            ))}
            {query.trim().length >= 2 && saved.length === 0 && off === null && (
              <li className="muted food-results__empty">{t("diary.noSaved")}</li>
            )}
          </ul>

          <div className="diary-actions">
            <button className="btn btn--ghost btn--sm" onClick={searchOff} disabled={offLoading || query.trim().length < 2}>
              {offLoading ? t("common.loading") : t("diary.searchOff")}
            </button>
            <button className="btn btn--ghost btn--sm" onClick={() => setShowCustom((s) => !s)}>
              {t("diary.custom")}
            </button>
          </div>

          <div className="diary-barcode">
            <input
              className="input"
              type="text"
              inputMode="numeric"
              placeholder={t("diary.barcodePlaceholder")}
              value={barcode}
              onChange={(e) => setBarcode(e.target.value)}
            />
            <button className="btn btn--ghost btn--sm" onClick={lookupBarcode}>
              {t("diary.lookup")}
            </button>
          </div>

          {showCustom && (
            <div className="custom-food">
              <input className="input" placeholder={t("diary.customName")} value={custom.name}
                onChange={(e) => setCustom({ ...custom, name: e.target.value })} />
              <div className="form__row">
                <input className="input" type="number" step="0.1" placeholder={t("diary.customKcal")} value={custom.kcal}
                  onChange={(e) => setCustom({ ...custom, kcal: e.target.value })} />
                <input className="input" type="number" step="0.1" placeholder={t("today.macros.protein")} value={custom.protein}
                  onChange={(e) => setCustom({ ...custom, protein: e.target.value })} />
              </div>
              <div className="form__row">
                <input className="input" type="number" step="0.1" placeholder={t("today.macros.fat")} value={custom.fat}
                  onChange={(e) => setCustom({ ...custom, fat: e.target.value })} />
                <input className="input" type="number" step="0.1" placeholder={t("today.macros.carbs")} value={custom.carbs}
                  onChange={(e) => setCustom({ ...custom, carbs: e.target.value })} />
              </div>
              <button className="btn btn--ghost btn--sm" onClick={useCustom}>{t("diary.useCustom")}</button>
            </div>
          )}

          {error && <div className="error">{error}</div>}

          {selected && (
            <div className="add-form">
              <div className="add-form__name">{selected.name} · {kcal(selected.per100_kcal)} / 100g</div>
              <div className="form__row">
                <label className="field">
                  <span>{t("diary.amount")}</span>
                  <input className="input" type="number" step="1" min="1" value={amount} onChange={(e) => setAmount(e.target.value)} />
                </label>
                <label className="field">
                  <span>{t("diary.slot")}</span>
                  <select className="select" value={slot} onChange={(e) => setSlot(e.target.value as MealSlot)}>
                    {MEAL_SLOTS.map((s) => (
                      <option key={s} value={s}>{t(`diary.slots.${s}`)}</option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="diary-actions">
                <button className="btn btn--primary btn--sm" onClick={logSelected}>{t("diary.add")}</button>
                <button className="btn btn--ghost btn--sm" onClick={() => setSelected(null)}>{t("diary.cancel")}</button>
              </div>
            </div>
          )}
        </Card>

        <Card
          title={t("diary.dayTitle")}
          action={
            <button className="btn btn--ghost btn--sm" onClick={copyYesterday}>{t("diary.copyYesterday")}</button>
          }
        >
          {MEAL_SLOTS.map((s) => {
            const entries = (day.data?.entries ?? []).filter((e) => e.slot === s);
            if (entries.length === 0) return null;
            return (
              <div className="slot-group" key={s}>
                <h3>{t(`diary.slots.${s}`)}</h3>
                <ul className="list">
                  {entries.map((e) => (
                    <li key={e.id} className="diary-entry">
                      <span className="diary-entry__name">{e.food_name}</span>
                      <span className="muted tnum">{oneDecimal(e.amount_g)} g</span>
                      <span className="tnum">{kcal(e.kcal)}</span>
                      <button className="icon-btn icon-btn--xs" onClick={() => editEntry(e)} aria-label={t("common.save")}>✎</button>
                      <button className="icon-btn icon-btn--xs" onClick={() => removeEntry(e.id)} aria-label={t("weight.delete")}>✕</button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
          {(day.data?.entries.length ?? 0) === 0 && <p className="muted">{t("diary.empty")}</p>}
          {totals && (
            <div className="result-row result-row--target diary-total">
              <span>{t("diary.total")}</span>
              <strong className="tnum">{kcal(totals.kcal)} kcal</strong>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
