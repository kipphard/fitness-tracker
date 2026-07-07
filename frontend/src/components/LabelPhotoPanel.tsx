import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";

import { apiUpload } from "../api/client";
import type { FoodLabelDraft } from "../api/types";
import { AiUnavailableNote } from "./AiUnavailableNote";
import { Card } from "./Card";

// Photo of a Nährwerttabelle → Claude vision → per-100g draft → prefill the custom-food form.
// Label reading is AI-only (no rule fallback is possible), so when Claude isn't configured we
// show the shared unavailable note instead of attempting the call. On success this panel hands
// the draft to the parent (which opens the prefilled custom modal) — it's just the loading /
// error surface for the extraction step.
export function LabelPhotoPanel({
  file,
  aiAvailable = true,
  onCancel,
  onExtracted,
}: {
  file: File;
  aiAvailable?: boolean;
  onCancel: () => void;
  onExtracted: (draft: FoodLabelDraft) => void;
}) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!aiAvailable) {
      setLoading(false); // AI off → show the unavailable note, don't call the API
      return;
    }
    let active = true;
    const form = new FormData();
    form.append("file", file);
    apiUpload<FoodLabelDraft>("/food/photo-label", form)
      .then((draft) => active && onExtracted(draft))
      .catch((e) => active && setError(e instanceof Error ? e.message : String(e)))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Card
      title={t("diary.labelTitle")}
      action={
        <button className="btn btn--ghost btn--sm" onClick={onCancel}>
          {t("diary.cancel")}
        </button>
      }
    >
      {!aiAvailable ? (
        <AiUnavailableNote />
      ) : loading ? (
        <p className="muted">{t("diary.readingLabel")}</p>
      ) : null}
      {error && (
        <>
          <div className="error">{error}</div>
          <button className="btn btn--ghost btn--sm" onClick={onCancel}>
            {t("diary.cancel")}
          </button>
        </>
      )}
    </Card>
  );
}
