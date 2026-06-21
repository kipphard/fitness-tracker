import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { apiGet, apiPut } from "../api/client";
import {
  ACTIVITY_LEVELS,
  GENDERS,
  GOALS,
  type ActivityLevelInfo,
  type CalorieResult,
  type Profile,
  type ProfileInput,
} from "../api/types";
import { kcal, oneDecimal } from "../lib/format";
import { Card } from "./Card";

const DEFAULTS: ProfileInput = {
  height_cm: "175",
  age: 30,
  gender: "male",
  weight_kg: "75",
  activity_level: "sedentary",
  goal: "maintain",
};

export function ProfileScreen() {
  const { t } = useTranslation();
  const [form, setForm] = useState<ProfileInput>(DEFAULTS);
  const [levels, setLevels] = useState<ActivityLevelInfo[]>([]);
  const [result, setResult] = useState<CalorieResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    apiGet<ActivityLevelInfo[]>("/calories/activity-levels")
      .then(setLevels)
      .catch(() => undefined);
    apiGet<Profile>("/profile")
      .then((p) => {
        setForm({
          height_cm: p.height_cm,
          age: p.age,
          gender: p.gender,
          weight_kg: p.weight_kg,
          activity_level: p.activity_level,
          goal: p.goal,
        });
        return apiGet<CalorieResult>("/calories/me");
      })
      .then((r) => r && setResult(r))
      .catch(() => undefined); // 404: no profile saved yet
  }, []);

  const set = <K extends keyof ProfileInput>(key: K, value: ProfileInput[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await apiPut<Profile>("/profile", { ...form, age: Number(form.age) });
      setResult(await apiGet<CalorieResult>("/calories/me"));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSaving(false);
    }
  };

  const multiplierFor = (key: string) => levels.find((l) => l.key === key)?.multiplier;

  return (
    <div className="screen">
      <header className="screen__head">
        <h1>{t("profile.title")}</h1>
        <p className="muted">{t("profile.subtitle")}</p>
      </header>

      <div className="grid grid--2">
        <Card>
          <form className="form" onSubmit={submit}>
            <div className="form__row">
              <label className="field">
                <span>{t("profile.height")}</span>
                <input
                  className="input"
                  type="number"
                  min="50"
                  max="260"
                  step="0.5"
                  required
                  value={form.height_cm}
                  onChange={(e) => set("height_cm", e.target.value)}
                />
              </label>
              <label className="field">
                <span>{t("profile.weight")}</span>
                <input
                  className="input"
                  type="number"
                  min="20"
                  max="400"
                  step="0.1"
                  required
                  value={form.weight_kg}
                  onChange={(e) => set("weight_kg", e.target.value)}
                />
              </label>
            </div>

            <div className="form__row">
              <label className="field">
                <span>{t("profile.age")}</span>
                <input
                  className="input"
                  type="number"
                  min="10"
                  max="120"
                  step="1"
                  required
                  value={form.age}
                  onChange={(e) => set("age", Number(e.target.value))}
                />
              </label>
              <label className="field">
                <span>{t("profile.gender")}</span>
                <select
                  className="select"
                  value={form.gender}
                  onChange={(e) => set("gender", e.target.value as ProfileInput["gender"])}
                >
                  {GENDERS.map((g) => (
                    <option key={g} value={g}>
                      {t(`profile.genderOptions.${g}`)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <label className="field">
              <span>{t("profile.activity")}</span>
              <select
                className="select"
                value={form.activity_level}
                onChange={(e) =>
                  set("activity_level", e.target.value as ProfileInput["activity_level"])
                }
              >
                {ACTIVITY_LEVELS.map((key) => {
                  const mult = multiplierFor(key);
                  return (
                    <option key={key} value={key}>
                      {t(`calories.levels.${key}.label`)}
                      {mult ? ` (×${oneDecimal(mult)})` : ""}
                    </option>
                  );
                })}
              </select>
            </label>

            <label className="field">
              <span>{t("profile.goal")}</span>
              <select
                className="select"
                value={form.goal}
                onChange={(e) => set("goal", e.target.value as ProfileInput["goal"])}
              >
                {GOALS.map((g) => (
                  <option key={g} value={g}>
                    {t(`profile.goalOptions.${g}`)}
                  </option>
                ))}
              </select>
            </label>

            {error && <div className="error">{error}</div>}
            <button className="btn btn--primary" type="submit" disabled={saving}>
              {saving ? t("common.saving") : t("profile.calculate")}
            </button>
          </form>
        </Card>

        <Card title={t("profile.results.title")}>
          {result ? (
            <div className="results">
              <div className="result-row">
                <span className="muted">{t("profile.results.bmr")}</span>
                <strong className="tnum">
                  {kcal(result.bmr)} <small>{t("profile.results.perDay")}</small>
                </strong>
              </div>
              <div className="result-row">
                <span className="muted">{t("profile.results.maintenance")}</span>
                <strong className="tnum">
                  {kcal(result.maintenance)} <small>{t("profile.results.perDay")}</small>
                </strong>
              </div>
              <div className="result-row result-row--target">
                <span>{t("profile.results.target")}</span>
                <strong className="tnum">
                  {kcal(result.target)} <small>{t("profile.results.perDay")}</small>
                </strong>
              </div>
              <div className="result-row">
                <span className="muted">{t("profile.results.factor")}</span>
                <span className="tnum">×{oneDecimal(result.activity_multiplier)}</span>
              </div>

              {result.below_floor && (
                <div className="alert alert--warn">
                  {t("profile.results.floorWarning", { floor: kcal(result.floor) })}
                </div>
              )}

              <div className="results__links">
                <Link to="/formula">{t("profile.results.learnFormula")}</Link>
                <Link to="/activity">{t("profile.results.learnActivity")}</Link>
              </div>
            </div>
          ) : (
            <p className="muted">{t("profile.subtitle")}</p>
          )}
        </Card>
      </div>
    </div>
  );
}
