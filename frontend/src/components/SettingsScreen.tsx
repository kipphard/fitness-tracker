import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiGet, apiPost, apiPut } from "../api/client";
import type { BackfillResult, Settings, UnitSystem } from "../api/types";
import { parseDecimalInput } from "../lib/format";
import { Card } from "./Card";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { MealSlotsSettings } from "./MealSlotsSettings";
import { SegmentedControl } from "./ui";

const UNIT_OPTIONS: UnitSystem[] = ["metric", "imperial"];

export function SettingsScreen() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [backfill, setBackfill] = useState<BackfillResult | null>(null);
  // Local draft for the free-text planning fields; persisted on blur.
  const [draft, setDraft] = useState({
    country: "",
    store: "",
    dietary: "",
    budget: "",
    currency: "",
    shoe: "",
  });

  const runBackfill = async () => {
    setBackfilling(true);
    setBackfill(null);
    try {
      setBackfill(await apiPost<BackfillResult>("/food/backfill-servings"));
    } catch {
      /* ignore — best-effort maintenance action */
    } finally {
      setBackfilling(false);
    }
  };

  useEffect(() => {
    apiGet<Settings>("/settings").then(setSettings).catch(() => undefined);
  }, []);

  useEffect(() => {
    if (settings)
      setDraft({
        country: settings.country ?? "",
        store: settings.store ?? "",
        dietary: settings.dietary_preferences ?? "",
        budget: settings.food_budget_weekly ?? "",
        currency: settings.currency ?? "",
        shoe: settings.shoe_size_eu ?? "",
      });
  }, [settings]);

  const save = async (patch: Partial<Settings>) => {
    const next = await apiPut<Settings>("/settings", patch);
    setSettings(next);
    setSaved(true);
    window.setTimeout(() => setSaved(false), 1500);
  };

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("settings.title")}</h1>
      </header>
      <Card>
        <div className="setting-row">
          <span>{t("settings.language")}</span>
          <LanguageSwitcher />
        </div>
        <div className="setting-row">
          <span>{t("settings.units")}</span>
          <SegmentedControl
            options={UNIT_OPTIONS.map((u) => ({
              value: u,
              label: t(`settings.unitOptions.${u}`),
            }))}
            value={settings?.unit_system ?? "metric"}
            onChange={(u) => save({ unit_system: u })}
          />
        </div>
        <div className="setting-row">
          <span>
            {t("settings.eatBack")}
            <small className="muted setting-sub">{t("settings.eatBackHint")}</small>
          </span>
          <label className="toggle">
            <input
              type="checkbox"
              checked={settings?.eat_back_activity ?? false}
              onChange={(e) => save({ eat_back_activity: e.target.checked })}
            />
            <span className="toggle__track" />
          </label>
        </div>
        <div className="setting-row">
          <span>
            {t("settings.shoeSize")}
            <small className="muted setting-sub">{t("settings.shoeSizeHint")}</small>
          </span>
          <input
            className="input select--auto"
            type="text"
            inputMode="decimal"
            value={draft.shoe}
            placeholder={t("settings.shoeSizePlaceholder")}
            onChange={(e) => setDraft((d) => ({ ...d, shoe: e.target.value }))}
            onBlur={() => {
              const raw = draft.shoe.trim();
              const v = raw === "" ? null : parseDecimalInput(raw);
              if (v === "") return; // ignore unparseable input
              if ((settings?.shoe_size_eu ?? "") !== (v ?? "")) save({ shoe_size_eu: v });
            }}
          />
        </div>
        <p className="muted setting-note">{t("settings.note")}</p>
        {saved && <div className="alert alert--ok">{t("settings.saved")}</div>}
      </Card>

      <MealSlotsSettings />

      <Card title={t("settings.planTitle")}>
        <p className="muted setting-note">{t("settings.planHint")}</p>
        <div className="setting-row">
          <span>{t("settings.country")}</span>
          <input
            className="input select--auto"
            value={draft.country}
            placeholder={t("settings.countryPlaceholder")}
            onChange={(e) => setDraft((d) => ({ ...d, country: e.target.value }))}
            onBlur={() => {
              if ((settings?.country ?? "") !== draft.country) save({ country: draft.country });
            }}
          />
        </div>
        <div className="setting-row">
          <span>{t("settings.store")}</span>
          <input
            className="input select--auto"
            value={draft.store}
            placeholder={t("settings.storePlaceholder")}
            onChange={(e) => setDraft((d) => ({ ...d, store: e.target.value }))}
            onBlur={() => {
              if ((settings?.store ?? "") !== draft.store) save({ store: draft.store });
            }}
          />
        </div>
        <label className="field">
          <span>{t("settings.dietaryPrefs")}</span>
          <textarea
            className="input"
            rows={2}
            value={draft.dietary}
            placeholder={t("settings.dietaryPlaceholder")}
            onChange={(e) => setDraft((d) => ({ ...d, dietary: e.target.value }))}
            onBlur={() => {
              if ((settings?.dietary_preferences ?? "") !== draft.dietary)
                save({ dietary_preferences: draft.dietary });
            }}
          />
        </label>
        <div className="setting-row">
          <span>{t("settings.budget")}</span>
          <input
            className="input select--auto"
            type="number"
            min="0"
            value={draft.budget}
            placeholder={t("settings.budgetPlaceholder")}
            onChange={(e) => setDraft((d) => ({ ...d, budget: e.target.value }))}
            onBlur={() => {
              if ((settings?.food_budget_weekly ?? "") !== draft.budget)
                save({ food_budget_weekly: draft.budget === "" ? null : draft.budget });
            }}
          />
        </div>
        <div className="setting-row">
          <span>{t("settings.currency")}</span>
          <input
            className="input select--auto"
            maxLength={3}
            value={draft.currency}
            placeholder="EUR"
            onChange={(e) => setDraft((d) => ({ ...d, currency: e.target.value.toUpperCase() }))}
            onBlur={() => {
              if ((settings?.currency ?? "") !== draft.currency)
                save({ currency: draft.currency === "" ? null : draft.currency });
            }}
          />
        </div>
        {saved && <div className="alert alert--ok">{t("settings.saved")}</div>}
      </Card>

      <Card title={t("settings.dataTitle")}>
        <div className="setting-row">
          <span>
            {t("settings.backfillServings")}
            <small className="muted setting-sub">{t("settings.backfillHint")}</small>
          </span>
          <button className="btn btn--ghost btn--sm" onClick={runBackfill} disabled={backfilling}>
            {backfilling ? t("common.loading") : t("settings.backfillRun")}
          </button>
        </div>
        {backfill && (
          <div className="alert alert--ok">
            {t("settings.backfillDone", { updated: backfill.updated, checked: backfill.checked })}
          </div>
        )}
      </Card>
    </div>
  );
}
