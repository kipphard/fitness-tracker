import { useTranslation } from "react-i18next";

import { vocabKey } from "../lib/exercise";

// Render a muscle list as localized chips (free-exercise-db muscle names → i18n).
export function MuscleChips({ muscles, max }: { muscles?: string[] | null; max?: number }) {
  const { t } = useTranslation();
  if (!muscles || muscles.length === 0) return null;
  const list = max ? muscles.slice(0, max) : muscles;
  return (
    <span className="muscle-chips">
      {list.map((m) => (
        <span key={m} className="muscle-chip">
          {t(`exercise.muscles.${vocabKey(m)}`, { defaultValue: m })}
        </span>
      ))}
    </span>
  );
}
