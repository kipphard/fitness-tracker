import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiGet, apiPut } from "../api/client";
import type { Settings, UnitSystem } from "../api/types";
import { Card } from "./Card";
import { LanguageSwitcher } from "./LanguageSwitcher";

const UNIT_OPTIONS: UnitSystem[] = ["metric", "imperial"];

export function SettingsScreen() {
  const { t } = useTranslation();
  const [settings, setSettings] = useState<Settings | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiGet<Settings>("/settings").then(setSettings).catch(() => undefined);
  }, []);

  const updateUnits = async (unit_system: UnitSystem) => {
    const next = await apiPut<Settings>("/settings", { unit_system });
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
            onChange={(e) => updateUnits(e.target.value as UnitSystem)}
          >
            {UNIT_OPTIONS.map((u) => (
              <option key={u} value={u}>
                {t(`settings.unitOptions.${u}`)}
              </option>
            ))}
          </select>
        </div>
        <p className="muted setting-note">{t("settings.note")}</p>
        {saved && <div className="alert alert--ok">{t("settings.saved")}</div>}
      </Card>
    </div>
  );
}
