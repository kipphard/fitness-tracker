import { useTranslation } from "react-i18next";

// Shown by every AI feature when Claude isn't configured (no API key / 503). Where a rule-based
// path exists the feature keeps working and this just explains the smarter option is off; where
// none exists (e.g. photo estimate) it stands in for the disabled action. See the AI-fallback
// convention in CLAUDE/memory.
export function AiUnavailableNote() {
  const { t } = useTranslation();
  return <div className="alert alert--info">{t("ai.unavailable")}</div>;
}
