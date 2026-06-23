import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiGet, apiPost, apiPut } from "../api/client";
import type { BackfillResult, Settings, UnitSystem } from "../api/types";
import { Card } from "./Card";
import { LanguageSwitcher } from "./LanguageSwitcher";

const UNIT_OPTIONS: UnitSystem[] = ["metric", "imperial"];

export function SettingsScreen() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);
  const [backfilling, setBackfilling] = useState(false);
  const [backfill, setBackfill] = useState<BackfillResult | null>(null);

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
          <select
            className="select select--auto"
            value={settings?.unit_system ?? "metric"}
            onChange={(e) => save({ unit_system: e.target.value as UnitSystem })}
          >
            {UNIT_OPTIONS.map((u) => (
              <option key={u} value={u}>
                {t(`settings.unitOptions.${u}`)}
              </option>
            ))}
          </select>
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
        <p className="muted setting-note">{t("settings.note")}</p>
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
