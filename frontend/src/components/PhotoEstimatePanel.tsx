import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiPost, apiUpload } from "../api/client";
import { MEAL_SLOTS, type MealSlot, type PhotoEstimate } from "../api/types";
import { kcal, num, oneDecimal } from "../lib/format";
import { AiUnavailableNote } from "./AiUnavailableNote";
import { Card } from "./Card";

// Photo → Claude vision estimate → review → log. The estimate gives absolute macros per item;
// logging derives per-100g so the existing diary scaling reproduces the same numbers. Photo
// estimation is AI-only (no rule fallback is possible), so when Claude isn't configured we show
// the shared unavailable note instead of attempting the call.
export function PhotoEstimatePanel({
  file,
  date,
  defaultSlot,
  aiAvailable = true,
  onClose,
}: {
  file: File;
  date: string;
  defaultSlot: MealSlot;
  aiAvailable?: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const [estimate, setEstimate] = useState<PhotoEstimate | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [answers, setAnswers] = useState("");
  const [slot, setSlot] = useState<MealSlot>(defaultSlot);
  const [busy, setBusy] = useState(false);

  const run = async (context?: string) => {
    setLoading(true);
    setError(null);
    const form = new FormData();
    form.append("file", file);
    if (context) form.append("context", context);
    try {
      setEstimate(await apiUpload<PhotoEstimate>("/food/photo", form));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (aiAvailable) void run();
    else setLoading(false); // AI off → show the unavailable note, don't call the API
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const logAll = async () => {
    if (!estimate) return;
    setBusy(true);
    try {
      for (const item of estimate.items) {
        const amount = num(item.amount_g);
        if (amount <= 0) continue;
        const factor = 100 / amount; // derive per-100g so diary scaling reproduces the estimate
        await apiPost("/diary", {
          date,
          slot,
          amount_g: item.amount_g,
          food: {
            name: item.name,
            per100_kcal: String(num(item.kcal) * factor),
            per100_protein_g: String(num(item.protein_g) * factor),
            per100_fat_g: String(num(item.fat_g) * factor),
            per100_carbs_g: String(num(item.carbs_g) * factor),
          },
        });
      }
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card
      title={t("diary.photoTitle")}
      action={
        <button className="btn btn--ghost btn--sm" onClick={onClose}>
          {t("diary.cancel")}
        </button>
      }
    >
      {aiAvailable ? (
        <div className="alert alert--info">{t("diary.photoDisclaimer")}</div>
      ) : (
        <AiUnavailableNote />
      )}

      {aiAvailable && loading && <p className="muted">{t("diary.estimating")}</p>}
      {error && <div className="error">{error}</div>}

      {estimate && !loading && (
        <>
          <ul className="list">
            {estimate.items.map((it, i) => (
              <li key={i} className="diary-entry">
                <span className="diary-entry__name">{it.name}</span>
                <span className="muted tnum">{oneDecimal(it.amount_g)} g</span>
                <span className="tnum">{kcal(it.kcal)} kcal</span>
              </li>
            ))}
          </ul>

          <div className="result-row result-row--target">
            <span>
              {t("diary.total")} · {t(`diary.confidence.${estimate.confidence}`)}
            </span>
            <strong className="tnum">{kcal(estimate.total.kcal)} kcal</strong>
          </div>
          {estimate.notes && <p className="muted">{estimate.notes}</p>}

          {estimate.questions.length > 0 && (
            <div className="photo-questions">
              <ul className="prose-list">
                {estimate.questions.map((q, i) => (
                  <li key={i}>{q}</li>
                ))}
              </ul>
              <textarea
                className="input"
                rows={2}
                placeholder={t("diary.answersPlaceholder")}
                value={answers}
                onChange={(e) => setAnswers(e.target.value)}
              />
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => run(answers)}
                disabled={!answers.trim()}
              >
                {t("diary.reestimate")}
              </button>
            </div>
          )}

          <div className="add-form">
            <label className="field">
              <span>{t("diary.slot")}</span>
              <select
                className="select"
                value={slot}
                onChange={(e) => setSlot(e.target.value as MealSlot)}
              >
                {MEAL_SLOTS.map((s) => (
                  <option key={s} value={s}>
                    {t(`diary.slots.${s}`)}
                  </option>
                ))}
              </select>
            </label>
            <button
              className="btn btn--primary"
              onClick={logAll}
              disabled={busy || estimate.items.length === 0}
            >
              {busy ? t("common.saving") : t("diary.logAll")}
            </button>
          </div>
        </>
      )}
    </Card>
  );
}
