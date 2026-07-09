import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiGet, apiPut } from "../../api/client";
import {
  ACTIVITY_LEVELS,
  GENDERS,
  GOALS,
  type ActivityLevel,
  type Gender,
  type Goal,
  type MyCalories,
  type Profile,
} from "../../api/types";
import { kcal, num } from "../../lib/format";
import { OptionCard, WizardShell } from "../ui";

const GOAL_ICON: Record<Goal, string> = { cut: "📉", maintain: "⚖️", bulk: "📈" };
const GENDER_ICON: Record<Gender, string> = { male: "♂️", female: "♀️" };
const ACTIVITY_ICON: Record<ActivityLevel, string> = {
  sedentary: "🪑",
  lightly_active: "🚶",
  moderately_active: "🏃",
  heavy: "🏋️",
  very_heavy: "🔥",
};

// The number-entry steps share this shape.
interface NumStep {
  key: "age" | "height" | "weight";
  title: string;
  value: string;
  set: (v: string) => void;
  unit: string;
  min: number;
  max: number;
  step: number;
}

const WELCOME = 0;
const GOAL = 1;
const GENDER = 2;
const AGE = 3;
const HEIGHT = 4;
const WEIGHT = 5;
const ACTIVITY = 6;
const SUMMARY = 7;
const TOTAL = 8;

// A short guided first-run wizard that collects exactly what the calorie engine
// needs and saves it via PUT /profile (no backend change). Shown when a signed-in
// user has no profile yet (gated in App.tsx).
export function OnboardingFlow({ onDone }: { onDone: () => void }) {
  const { t } = useTranslation();
  const [step, setStep] = useState(WELCOME);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [gender, setGender] = useState<Gender | null>(null);
  const [age, setAge] = useState("30");
  const [height, setHeight] = useState("175");
  const [weight, setWeight] = useState("75");
  const [activity, setActivity] = useState<ActivityLevel | null>(null);
  const [result, setResult] = useState<MyCalories | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const numSteps: Record<number, NumStep> = {
    [AGE]: { key: "age", title: t("onboarding.ageTitle"), value: age, set: setAge, unit: t("onboarding.years"), min: 10, max: 120, step: 1 },
    [HEIGHT]: { key: "height", title: t("onboarding.heightTitle"), value: height, set: setHeight, unit: "cm", min: 50, max: 260, step: 1 },
    [WEIGHT]: { key: "weight", title: t("onboarding.weightTitle"), value: weight, set: setWeight, unit: "kg", min: 20, max: 400, step: 0.1 },
  };

  const canAdvance = useMemo(() => {
    switch (step) {
      case GOAL:
        return goal !== null;
      case GENDER:
        return gender !== null;
      case AGE:
        return num(age) >= 10 && num(age) <= 120;
      case HEIGHT:
        return num(height) >= 50 && num(height) <= 260;
      case WEIGHT:
        return num(weight) >= 20 && num(weight) <= 400;
      case ACTIVITY:
        return activity !== null;
      default:
        return true;
    }
  }, [step, goal, gender, age, height, weight, activity]);

  const finish = async () => {
    if (!goal || !gender || !activity) return;
    setSaving(true);
    setError(null);
    try {
      await apiPut<Profile>("/profile", {
        height_cm: height,
        age: Number(age),
        gender,
        weight_kg: weight,
        activity_level: activity,
        goal,
      });
      setResult(await apiGet<MyCalories>("/calories/me"));
      setStep(SUMMARY);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setSaving(false);
    }
  };

  const body = () => {
    if (step === WELCOME || step === SUMMARY) {
      const done = step === SUMMARY;
      return (
        <div className="onboarding-hero">
          <div className="onboarding-emoji">{done ? "🎉" : "🎯"}</div>
          <h1>{t(done ? "onboarding.summaryTitle" : "onboarding.welcomeTitle")}</h1>
          <p className="muted">{t(done ? "onboarding.summaryBody" : "onboarding.welcomeBody")}</p>
          {done && (
            <div className="onboarding-plan">
              <span className="muted">{t("onboarding.dailyTarget")}</span>
              <strong className="onboarding-plan__kcal tnum">
                {kcal(result?.target ?? 0)} kcal
              </strong>
            </div>
          )}
        </div>
      );
    }
    if (step === GOAL) {
      return (
        <>
          <h1>{t("onboarding.goalTitle")}</h1>
          <div className="option-list">
            {GOALS.map((g) => (
              <OptionCard
                key={g}
                icon={GOAL_ICON[g]}
                label={t(`profile.goalOptions.${g}`)}
                selected={goal === g}
                onSelect={() => setGoal(g)}
              />
            ))}
          </div>
        </>
      );
    }
    if (step === GENDER) {
      return (
        <>
          <h1>{t("onboarding.genderTitle")}</h1>
          <p className="muted">{t("onboarding.genderHint")}</p>
          <div className="option-list">
            {GENDERS.map((g) => (
              <OptionCard
                key={g}
                icon={GENDER_ICON[g]}
                label={t(`profile.genderOptions.${g}`)}
                selected={gender === g}
                onSelect={() => setGender(g)}
              />
            ))}
          </div>
        </>
      );
    }
    if (step === ACTIVITY) {
      return (
        <>
          <h1>{t("onboarding.activityTitle")}</h1>
          <div className="option-list">
            {ACTIVITY_LEVELS.map((lvl) => (
              <OptionCard
                key={lvl}
                icon={ACTIVITY_ICON[lvl]}
                label={t(`calories.levels.${lvl}.label`)}
                description={t(`calories.levels.${lvl}.desc`)}
                selected={activity === lvl}
                onSelect={() => setActivity(lvl)}
              />
            ))}
          </div>
        </>
      );
    }
    const ns = numSteps[step];
    return (
      <>
        <h1>{ns.title}</h1>
        <div className="onboarding-num">
          <input
            className="input onboarding-num__input"
            type="number"
            inputMode="decimal"
            min={ns.min}
            max={ns.max}
            step={ns.step}
            value={ns.value}
            onChange={(e) => ns.set(e.target.value)}
            autoFocus
          />
          <span className="onboarding-num__unit muted">{ns.unit}</span>
        </div>
      </>
    );
  };

  const footer = () => {
    if (step === WELCOME) {
      return (
        <button className="btn btn--primary btn--block" onClick={() => setStep(GOAL)}>
          {t("onboarding.start")}
        </button>
      );
    }
    if (step === SUMMARY) {
      return (
        <button className="btn btn--primary btn--block" onClick={onDone}>
          {t("onboarding.enterApp")}
        </button>
      );
    }
    if (step === ACTIVITY) {
      return (
        <button
          className="btn btn--primary btn--block"
          onClick={finish}
          disabled={!canAdvance || saving}
        >
          {saving ? t("onboarding.saving") : t("onboarding.next")}
        </button>
      );
    }
    return (
      <button
        className="btn btn--primary btn--block"
        onClick={() => setStep((s) => s + 1)}
        disabled={!canAdvance}
      >
        {t("onboarding.next")}
      </button>
    );
  };

  return (
    <WizardShell
      progress={step / (TOTAL - 1)}
      onBack={step > WELCOME && step < SUMMARY ? () => setStep((s) => s - 1) : undefined}
      footer={footer()}
    >
      {body()}
      {error && <div className="error">{error}</div>}
    </WizardShell>
  );
}
