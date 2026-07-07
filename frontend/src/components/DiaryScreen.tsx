import { Suspense, lazy, useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiDelete, apiGet, apiPatch, apiPost } from "../api/client";
import {
  type DiaryDay,
  type DiaryEntry,
  type Food,
  type FoodData,
  type MealSlot,
} from "../api/types";
import { useApi } from "../hooks/useApi";
import { useMealSlots, useSlotLabel } from "../hooks/useMealSlots";
import { addDays, kcal, num, oneDecimal, todayIso } from "../lib/format";
import { Card } from "./Card";
import { Modal } from "./Modal";

// Lazy so the ZXing barcode library only loads when the user opens the scanner.
const BarcodeScanner = lazy(() =>
  import("./BarcodeScanner").then((m) => ({ default: m.BarcodeScanner })),
);

interface Selectable {
  id?: string;
  name: string;
  per100_kcal: string;
  per100_protein_g: string;
  per100_fat_g: string;
  per100_carbs_g: string;
  serving_g?: string | null;
  barcode?: string | null;
}

function toSelectable(f: Food | FoodData): Selectable {
  return {
    id: "id" in f ? f.id : undefined,
    name: f.name,
    per100_kcal: f.per100_kcal,
    per100_protein_g: f.per100_protein_g,
    per100_fat_g: f.per100_fat_g,
    per100_carbs_g: f.per100_carbs_g,
    serving_g: f.serving_g,
    barcode: f.barcode,
  };
}

const EMPTY_CUSTOM = { name: "", kcal: "", protein: "", fat: "", carbs: "", serving: "" };

export function DiaryScreen() {
  const { t } = useTranslation();
  const [date, setDate] = useState(todayIso());
  const day = useApi<DiaryDay>(`/diary?date=${date}`);
  const recent = useApi<Food[]>("/diary/recent");

  const { slots } = useMealSlots();
  const slotLabel = useSlotLabel(slots);

  // Which meal's "add food" sheet is open (null = closed). Drives the whole add flow.
  const [addSlot, setAddSlot] = useState<MealSlot | null>(null);
  const [query, setQuery] = useState("");
  const [saved, setSaved] = useState<Food[]>([]);
  const [off, setOff] = useState<FoodData[] | null>(null);
  const [offLoading, setOffLoading] = useState(false);
  const [barcode, setBarcode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showScanner, setShowScanner] = useState(false);
  const [showAllRecent, setShowAllRecent] = useState(false);
  const [showCustom, setShowCustom] = useState(false);
  const [custom, setCustom] = useState(EMPTY_CUSTOM);

  // Food detail modal (a picked food being portioned) + the meal it goes to.
  const [selected, setSelected] = useState<Selectable | null>(null);
  const [amount, setAmount] = useState("100");
  const [slot, setSlot] = useState<MealSlot>("breakfast");
  const [servingEdit, setServingEdit] = useState("");

  // Edit-entry modal.
  const [editing, setEditing] = useState<DiaryEntry | null>(null);
  const [editAmount, setEditAmount] = useState("");

  // Search the user's saved foods as they type (only while the add sheet is open).
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

  useEffect(() => {
    setServingEdit(selected?.serving_g ?? "");
  }, [selected]);

  const openAdd = (s: MealSlot) => {
    setAddSlot(s);
    setSlot(s);
    setQuery("");
    setOff(null);
    setShowCustom(false);
    setSelected(null);
    setError(null);
  };
  const closeAdd = () => {
    setAddSlot(null);
    setSelected(null);
    setShowCustom(false);
    setQuery("");
    setOff(null);
  };

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

  const selectByBarcode = async (code: string) => {
    if (!code.trim()) return;
    setError(null);
    try {
      setSelected(
        toSelectable(await apiGet<Food>(`/food/barcode/${encodeURIComponent(code.trim())}`)),
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };
  const lookupBarcode = async () => {
    await selectByBarcode(barcode);
    setBarcode("");
  };

  const useCustom = () => {
    if (!custom.name.trim() || !custom.kcal) return;
    setSelected({
      name: custom.name.trim(),
      per100_kcal: custom.kcal,
      per100_protein_g: custom.protein || "0",
      per100_fat_g: custom.fat || "0",
      per100_carbs_g: custom.carbs || "0",
      serving_g: custom.serving && num(custom.serving) > 0 ? custom.serving : null,
    });
    setShowCustom(false);
    setCustom(EMPTY_CUSTOM);
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
        serving_g:
          selected.serving_g && num(selected.serving_g) > 0 ? selected.serving_g : null,
        barcode: selected.barcode ?? null,
      };
    try {
      await apiPost("/diary", body);
      setSelected(null); // back to the add sheet so they can add more to this meal
      setAmount("100");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const saveServing = async () => {
    if (!selected?.id) return;
    const v = num(servingEdit);
    if (v <= 0) return;
    try {
      const updated = await apiPatch<Food>(`/food/${selected.id}`, { serving_g: String(v) });
      setSelected({ ...selected, serving_g: updated.serving_g });
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  const openEdit = (entry: DiaryEntry) => {
    setEditing(entry);
    setEditAmount(String(num(entry.amount_g)));
  };
  const saveEdit = async () => {
    if (!editing) return;
    const n = num(editAmount);
    if (n <= 0) return;
    const entry = editing;
    setEditing(null);
    await apiPatch(`/diary/${entry.id}`, { amount_g: String(n) }).catch(() => undefined);
  };
  const deleteEditing = async () => {
    if (!editing) return;
    const id = editing.id;
    setEditing(null);
    await apiDelete(`/diary/${id}`).catch(() => undefined);
  };

  const scaleEntry = (entry: DiaryEntry, newAmount: string) => {
    const f = num(newAmount) / (num(entry.amount_g) || 1);
    return {
      kcal: num(entry.kcal) * f,
      protein: num(entry.protein_g) * f,
      carbs: num(entry.carbs_g) * f,
      fat: num(entry.fat_g) * f,
    };
  };
  const sumMacros = (es: DiaryEntry[]) =>
    es.reduce(
      (a, e) => ({
        kcal: a.kcal + num(e.kcal),
        protein: a.protein + num(e.protein_g),
        carbs: a.carbs + num(e.carbs_g),
        fat: a.fat + num(e.fat_g),
      }),
      { kcal: 0, protein: 0, carbs: 0, fat: 0 },
    );

  const copyYesterday = () =>
    apiPost("/diary/copy", { from_date: addDays(date, -1), to_date: date }).catch(() => undefined);

  const searching = query.trim().length >= 2;
  const results = searching ? saved : recent.data ?? [];
  const COLLAPSED_RECENT = 6;
  const visibleResults = searching || showAllRecent ? results : results.slice(0, COLLAPSED_RECENT);

  const factor = num(amount) / 100;
  const scaledMacros = selected
    ? {
        kcal: num(selected.per100_kcal) * factor,
        protein: num(selected.per100_protein_g) * factor,
        carbs: num(selected.per100_carbs_g) * factor,
        fat: num(selected.per100_fat_g) * factor,
      }
    : null;
  const totals = day.data?.totals;
  const editScaled = editing ? scaleEntry(editing, editAmount) : null;

  // Render the user's slots in order, plus any slot an existing entry uses that isn't in the list
  // (e.g. an entry logged to a since-deleted custom slot) so no logged food is ever hidden.
  const knownSlotKeys = new Set(slots.map((s) => s.key));
  const orphanSlotKeys = [...new Set((day.data?.entries ?? []).map((e) => e.slot))].filter(
    (k) => !knownSlotKeys.has(k),
  );
  const slotKeys = [...slots.map((s) => s.key), ...orphanSlotKeys];

  return (
    <div className="screen">
      {showScanner && (
        <Suspense fallback={null}>
          <BarcodeScanner
            onScan={(code) => {
              setShowScanner(false);
              void selectByBarcode(code);
            }}
            onClose={() => setShowScanner(false)}
          />
        </Suspense>
      )}

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

      <Card
        title={t("diary.dayTitle")}
        action={
          <button className="btn btn--ghost btn--sm" onClick={copyYesterday}>{t("diary.copyYesterday")}</button>
        }
      >
        {slotKeys.map((s) => {
          const entries = (day.data?.entries ?? []).filter((e) => e.slot === s);
          const mt = sumMacros(entries);
          return (
            <div className="slot-group" key={s}>
              <div className="slot-group__head">
                <h3>{slotLabel(s)}</h3>
                {entries.length > 0 && <span className="muted tnum">{kcal(mt.kcal)} kcal</span>}
              </div>
              {entries.length > 0 && (
                <ul className="list">
                  {entries.map((e) => (
                    <li key={e.id} className="diary-row">
                      <button className="diary-entry__row" onClick={() => openEdit(e)}>
                        <span className="diary-entry__name">{e.food_name}</span>
                        <span className="muted tnum">{oneDecimal(e.amount_g)} g</span>
                        <span className="tnum diary-entry__kcal">{kcal(e.kcal)}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
              <button className="slot-group__add" onClick={() => openAdd(s)}>
                + {t("diary.addFood")}
              </button>
            </div>
          );
        })}

        {totals && (day.data?.entries.length ?? 0) > 0 && (
          <div className="diary-total">
            <div className="result-row result-row--target">
              <span>{t("diary.total")}</span>
              <strong className="tnum">{kcal(totals.kcal)} kcal</strong>
            </div>
            <div className="add-form__macros diary-total__macros">
              <span><strong className="tnum">{oneDecimal(totals.protein_g)} g</strong> {t("today.macros.protein")}</span>
              <span><strong className="tnum">{oneDecimal(totals.carbs_g)} g</strong> {t("today.macros.carbs")}</span>
              <span><strong className="tnum">{oneDecimal(totals.fat_g)} g</strong> {t("today.macros.fat")}</span>
            </div>
          </div>
        )}
      </Card>

      {/* ── Add-food sheet (per meal) ─────────────────────────────────────── */}
      {addSlot && (
        <Modal title={t("diary.addToMeal", { meal: slotLabel(addSlot) })} onClose={closeAdd}>
          <input
            className="input"
            type="search"
            placeholder={t("diary.searchPlaceholder")}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />

          <div className="diary-actions diary-actions--wrap">
            <button className="btn btn--ghost btn--sm" onClick={searchOff} disabled={offLoading || query.trim().length < 2}>
              {offLoading ? t("common.loading") : t("diary.searchOff")}
            </button>
            <button className="btn btn--ghost btn--sm" onClick={() => setShowCustom(true)}>
              {t("diary.custom")}
            </button>
            <button className="btn btn--ghost btn--sm" onClick={() => setShowScanner(true)}>
              📷 {t("diary.scanBarcode")}
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

          {error && <div className="error">{error}</div>}

          {!searching && results.length > 0 && (
            <div className="food-recent__head">{t("diary.recentTitle")}</div>
          )}
          <ul className="food-results">
            {visibleResults.map((f) => (
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
            {searching && saved.length === 0 && off === null && (
              <li className="muted food-results__empty">{t("diary.noSaved")}</li>
            )}
          </ul>

          {!searching && results.length > COLLAPSED_RECENT && (
            <button
              className="btn btn--link btn--sm food-recent__toggle"
              onClick={() => setShowAllRecent((s) => !s)}
            >
              {showAllRecent
                ? t("diary.showLessRecent")
                : t("diary.showMoreRecent", { count: results.length - COLLAPSED_RECENT })}
            </button>
          )}
        </Modal>
      )}

      {/* ── Food detail (portion + meal) ──────────────────────────────────── */}
      {selected && (
        <Modal
          title={selected.name}
          onClose={() => setSelected(null)}
          footer={
            <div className="diary-actions">
              <button className="btn btn--primary" onClick={logSelected}>{t("diary.add")}</button>
              <button className="btn btn--ghost" onClick={() => setSelected(null)}>{t("diary.cancel")}</button>
            </div>
          }
        >
          <div className="muted">{kcal(selected.per100_kcal)} kcal / 100g</div>
          <div className="form__row">
            <label className="field">
              <span>{t("diary.amount")}</span>
              <input className="input" type="number" step="1" min="1" inputMode="numeric" value={amount} autoFocus onChange={(e) => setAmount(e.target.value)} />
            </label>
            <label className="field">
              <span>{t("diary.slot")}</span>
              <select className="select" value={slot} onChange={(e) => setSlot(e.target.value as MealSlot)}>
                {slots.map((sdef) => (
                  <option key={sdef.key} value={sdef.key}>{slotLabel(sdef.key)}</option>
                ))}
              </select>
            </label>
          </div>
          {scaledMacros && (
            <div className="add-form__macros">
              <span><strong className="tnum">{kcal(scaledMacros.kcal)}</strong> kcal</span>
              <span><strong className="tnum">{oneDecimal(scaledMacros.protein)} g</strong> {t("today.macros.protein")}</span>
              <span><strong className="tnum">{oneDecimal(scaledMacros.carbs)} g</strong> {t("today.macros.carbs")}</span>
              <span><strong className="tnum">{oneDecimal(scaledMacros.fat)} g</strong> {t("today.macros.fat")}</span>
            </div>
          )}
          {selected.id && (
            <div className="serving-edit">
              <label className="field serving-edit__field">
                <span>{t("diary.serving")}</span>
                <input className="input" type="number" step="1" min="1" inputMode="numeric" value={servingEdit} onChange={(e) => setServingEdit(e.target.value)} />
              </label>
              <button className="btn btn--ghost btn--sm" onClick={saveServing}>{t("diary.saveServing")}</button>
            </div>
          )}
        </Modal>
      )}

      {/* ── Custom food ───────────────────────────────────────────────────── */}
      {showCustom && (
        <Modal
          title={t("diary.custom")}
          onClose={() => setShowCustom(false)}
          footer={
            <div className="diary-actions">
              <button className="btn btn--primary" onClick={useCustom} disabled={!custom.name.trim() || !custom.kcal}>{t("diary.useCustom")}</button>
              <button className="btn btn--ghost" onClick={() => setShowCustom(false)}>{t("diary.cancel")}</button>
            </div>
          }
        >
          <input className="input" placeholder={t("diary.customName")} value={custom.name}
            onChange={(e) => setCustom({ ...custom, name: e.target.value })} autoFocus />
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
          <input className="input" type="number" step="1" min="1" placeholder={t("diary.servingOptional")} value={custom.serving}
            onChange={(e) => setCustom({ ...custom, serving: e.target.value })} />
        </Modal>
      )}

      {/* ── Edit a logged entry ───────────────────────────────────────────── */}
      {editing && (
        <Modal
          title={editing.food_name}
          onClose={() => setEditing(null)}
          footer={
            <div className="diary-actions diary-actions--split">
              <button className="btn btn--danger btn--sm" onClick={deleteEditing}>{t("diary.delete")}</button>
              <div className="diary-actions">
                <button className="btn btn--primary" onClick={saveEdit}>{t("common.save")}</button>
                <button className="btn btn--ghost" onClick={() => setEditing(null)}>{t("diary.cancel")}</button>
              </div>
            </div>
          }
        >
          <label className="field">
            <span>{t("diary.amount")}</span>
            <input className="input" type="number" step="1" min="1" inputMode="numeric" value={editAmount} autoFocus onChange={(e) => setEditAmount(e.target.value)} />
          </label>
          {editScaled && (
            <div className="add-form__macros">
              <span><strong className="tnum">{kcal(editScaled.kcal)}</strong> kcal</span>
              <span><strong className="tnum">{oneDecimal(editScaled.protein)} g</strong> {t("today.macros.protein")}</span>
              <span><strong className="tnum">{oneDecimal(editScaled.carbs)} g</strong> {t("today.macros.carbs")}</span>
              <span><strong className="tnum">{oneDecimal(editScaled.fat)} g</strong> {t("today.macros.fat")}</span>
            </div>
          )}
        </Modal>
      )}

    </div>
  );
}
