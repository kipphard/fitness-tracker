import { useTranslation } from "react-i18next";

import { MEAL_SLOTS, type MealSlotDef } from "../api/types";
import { useApi } from "./useApi";

// Built-ins as a fallback before /meal-slots loads (and if it ever errors).
const DEFAULT_SLOTS: MealSlotDef[] = MEAL_SLOTS.map((key) => ({
  key,
  label: null,
  builtin: true,
}));

// The user's meal slots (built-ins + their custom ones), refetched on any app mutation via useApi.
export function useMealSlots(): { slots: MealSlotDef[]; loading: boolean; reload: () => void } {
  const { data, loading, reload } = useApi<MealSlotDef[]>("/meal-slots");
  return { slots: data ?? DEFAULT_SLOTS, loading, reload };
}

// A label function for a slot key: built-ins translated by key, customs shown with their label.
// Falls back to the key itself for an unknown slot (e.g. an entry logged to a since-deleted slot).
export function useSlotLabel(slots: MealSlotDef[]): (key: string) => string {
  const { t } = useTranslation();
  return (key: string) => {
    const def = slots.find((s) => s.key === key);
    if (def && !def.builtin) return def.label ?? key;
    return t(`diary.slots.${key}`, { defaultValue: def?.label ?? key });
  };
}
