import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { apiGet, apiPut } from "../api/client";
import {
  ACTIVITY_LEVELS,
  GENDERS,
  GOALS,
  type ActivityLevelInfo,
  type MyCalories,
  type Profile,
  type ProfileInput,
} from "../api/types";
import { kcal, oneDecimal } from "../lib/format";
import { Card } from "./Card";
import { OptionCard } from "./ui";

const DEFAULTS: ProfileInput = {
  height_cm: "175",
  age: 30,
  gender: "male",
  weight_kg: "75",
  activity_level: "sedentary",
  goal: "maintain",
};

const GOAL_ICON: Record<string, string> = { cut: "📉", maintain: "⚖️", bulk: "📈" };
const GENDER_ICON: Record<string, string> = { male: "♂️", female: "♀️" };
const ACTIVITY_ICON: Record<string, string> = {
  sedentary: "🪑",
  lightly_active: "🚶",
  moderately_active: "🏃",
  heavy: "🏋️",
  very_heavy: "🔥",
};

export function ProfileScreen() {
  const { t } = useTranslation();
  const [form, setForm] = useState<ProfileInput>(DEFAULTS);
  const [levels, setLevels] = useState<ActivityLevelInfo[]>([]);
  const [result, setResult] = useState<MyCalories | null>(null);
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
        return apiGet<MyCalories>("/calories/me");
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
      setResult(await apiGet<MyCalories>("/calories/me"));
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

            <div className="field">
              <span>{t("profile.gender")}</span>
              <div className="option-list option-list--row">
                {GENDERS.map((g) => (
                  <OptionCard
                    key={g}
                    icon={GENDER_ICON[g]}
                    label={t(`profile.genderOptions.${g}`)}
                    selected={form.gender === g}
                    onSelect={() => set("gender", g)}
                  />
                ))}
              </div>
            </div>

            <div className="field">
              <span>{t("profile.goal")}</span>
              <div className="option-list">
                {GOALS.map((g) => (
                  <OptionCard
                    key={g}
                    icon={GOAL_ICON[g]}
                    label={t(`profile.goalOptions.${g}`)}
                    selected={form.goal === g}
                    onSelect={() => set("goal", g)}
                  />
                ))}
              </div>
            </div>

            <div className="field">
              <span>{t("profile.activity")}</span>
              <div className="option-list">
                {ACTIVITY_LEVELS.map((key) => {
                  const mult = multiplierFor(key);
                  return (
                    <OptionCard
                      key={key}
                      icon={ACTIVITY_ICON[key]}
                      label={t(`calories.levels.${key}.label`)}
                      description={`${t(`calories.levels.${key}.desc`)}${
                        mult ? ` · ×${oneDecimal(mult)}` : ""
                      }`}
                      selected={form.activity_level === key}
                      onSelect={() => set("activity_level", key)}
                    />
                  );
                })}
              </div>
            </div>

            {error && <div className="error">{error}</div>}
            <button className="btn btn--primary btn--block" type="submit" disabled={saving}>
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

              <p className="muted results__basis">
                {t("profile.results.weightBasis", { weight: oneDecimal(result.weight_kg) })} ·{" "}
                {t(`profile.results.source.${result.weight_source}`)}
              </p>

              <div className="results__links">
                <Link to="/weight">{t("profile.results.logWeight")}</Link>
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
