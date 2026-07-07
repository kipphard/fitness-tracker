import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiGet, apiPut } from "../api/client";
import type { MealSlotDef } from "../api/types";
import { Card } from "./Card";

interface Row {
  key: string;
  label: string;
  builtin: boolean;
}

// Manage user-defined meal slots: reorder any, rename/delete/add custom ones. Built-ins are
// always present and can't be renamed or removed. Saved as a whole ordered list via PUT — the
// non-GET request fires "fit-data-changed", so the diary's slot list refetches automatically.
export function MealSlotsSettings() {
  const { t } = useTranslation();
  const [rows, setRows] = useState<Row[] | null>(null);
  const [saving, setSaving] = useState(false);
  const [dirty, setDirty] = useState(false);
  const [saved, setSaved] = useState(false);
  const tempId = useRef(0);

  const load = (defs: MealSlotDef[]) =>
    setRows(defs.map((d) => ({ key: d.key, label: d.label ?? "", builtin: d.builtin })));

  useEffect(() => {
    apiGet<MealSlotDef[]>("/meal-slots").then(load).catch(() => undefined);
  }, []);

  const update = (next: Row[]) => {
    setRows(next);
    setDirty(true);
  };

  const move = (i: number, dir: -1 | 1) => {
    if (!rows) return;
    const j = i + dir;
    if (j < 0 || j >= rows.length) return;
    const next = rows.slice();
    [next[i], next[j]] = [next[j], next[i]];
    update(next);
  };
  const rename = (i: number, label: string) => {
    if (!rows) return;
    const next = rows.slice();
    next[i] = { ...next[i], label };
    update(next);
  };
  const remove = (i: number) => rows && update(rows.filter((_, k) => k !== i));
  const add = () =>
    rows && update([...rows, { key: `new-${tempId.current++}`, label: "", builtin: false }]);

  const save = async () => {
    if (!rows) return;
    setSaving(true);
    try {
      // New rows have a temp "new-*" key → send null so the backend mints a stable custom key.
      const result = await apiPut<MealSlotDef[]>("/meal-slots", {
        slots: rows.map((r) => ({
          key: r.key.startsWith("new-") ? null : r.key,
          label: r.label,
        })),
      });
      load(result);
      setDirty(false);
      setSaved(true);
      window.setTimeout(() => setSaved(false), 1500);
    } finally {
      setSaving(false);
    }
  };

  if (!rows) return null;

  return (
    <Card title={t("settings.mealSlotsTitle")}>
      <p className="muted setting-note">{t("settings.mealSlotsHint")}</p>
      <ul className="list">
        {rows.map((r, i) => (
          <li key={r.key} className="slot-edit-row">
            {r.builtin ? (
              <span className="slot-edit-row__name">{t(`diary.slots.${r.key}`)}</span>
            ) : (
              <input
                className="input slot-edit-row__input"
                value={r.label}
                placeholder={t("settings.mealSlotName")}
                onChange={(e) => rename(i, e.target.value)}
              />
            )}
            <div className="slot-edit-row__actions">
              <button
                className="icon-btn"
                onClick={() => move(i, -1)}
                disabled={i === 0}
                aria-label={t("settings.moveUp")}
              >
                ↑
              </button>
              <button
                className="icon-btn"
                onClick={() => move(i, 1)}
                disabled={i === rows.length - 1}
                aria-label={t("settings.moveDown")}
              >
                ↓
              </button>
              {!r.builtin && (
                <button
                  className="icon-btn"
                  onClick={() => remove(i)}
                  aria-label={t("diary.delete")}
                >
                  ✕
                </button>
              )}
            </div>
          </li>
        ))}
      </ul>
      <div className="diary-actions">
        <button className="btn btn--ghost btn--sm" onClick={add}>
          + {t("settings.addMealSlot")}
        </button>
        <button className="btn btn--primary btn--sm" onClick={save} disabled={saving || !dirty}>
          {saving ? t("common.saving") : t("common.save")}
        </button>
      </div>
      {saved && <div className="alert alert--ok">{t("settings.saved")}</div>}
    </Card>
  );
}
