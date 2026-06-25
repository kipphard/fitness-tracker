import { useState } from "react";
import { useTranslation } from "react-i18next";

import type { Settings } from "../api/types";
import { useApi } from "../hooks/useApi";
import { parseDecimalInput } from "../lib/format";
import { distanceToSteps, PACES, type Pace } from "../lib/steps";

// A small "km → steps" helper for cardio machines that show distance but not steps (#13).
// Uses the shoe-size setting as a rough stride basis; the result is added to the day's steps.
export function StepsFromDistance({ onAdd }: { onAdd: (steps: number) => void }) {
  const { t } = useTranslation();
  const settings = useApi<Settings>("/settings");
  const [open, setOpen] = useState(false);
  const [km, setKm] = useState("");
  const [pace, setPace] = useState<Pace>("walking");

  const shoe = settings.data?.shoe_size_eu ? Number(settings.data.shoe_size_eu) : null;
  const steps = distanceToSteps(Number(parseDecimalInput(km) || "0"), shoe, pace);

  return (
    <div className="km-steps">
      <button className="btn btn--link btn--sm" onClick={() => setOpen((o) => !o)}>
        {open ? "▾" : "▸"} {t("today.kmToSteps")}
      </button>
      {open && (
        <>
          <div className="km-steps__form">
            <input
              className="input"
              type="text"
              inputMode="decimal"
              placeholder={t("today.distanceKm")}
              value={km}
              onChange={(e) => setKm(e.target.value)}
            />
            <select className="select" value={pace} onChange={(e) => setPace(e.target.value as Pace)}>
              {PACES.map((p) => (
                <option key={p} value={p}>
                  {t(`today.pace.${p}`)}
                </option>
              ))}
            </select>
            <span className="muted tnum">
              ≈ {steps} {t("today.stepsUnit")}
            </span>
            <button
              className="btn btn--ghost btn--sm"
              disabled={steps <= 0}
              onClick={() => {
                onAdd(steps);
                setKm("");
                setOpen(false);
              }}
            >
              {t("today.addSteps")}
            </button>
          </div>
          {!shoe && <p className="muted setting-sub">{t("today.shoeHint")}</p>}
        </>
      )}
    </div>
  );
}
