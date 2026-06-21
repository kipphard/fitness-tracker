import { useTranslation } from "react-i18next";

import { apiPut, getToken } from "../api/client";
import { SUPPORTED_LANGUAGES } from "../i18n";

const LABELS: Record<string, string> = { en: "EN", de: "DE" };

export function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const current = i18n.resolvedLanguage ?? i18n.language ?? "en";

  const change = (code: string) => {
    if (code === current) return;
    void i18n.changeLanguage(code);
    document.documentElement.lang = code;
    // Best-effort persistence to the user's settings (ignored if logged out / offline).
    if (getToken()) apiPut("/settings", { language: code }).catch(() => undefined);
  };

  return (
    <div className="lang-switch" role="group" aria-label="Language">
      {SUPPORTED_LANGUAGES.map((code) => (
        <button
          key={code}
          type="button"
          className={"lang-switch__btn" + (current.startsWith(code) ? " is-active" : "")}
          aria-pressed={current.startsWith(code)}
          onClick={() => change(code)}
        >
          {LABELS[code] ?? code.toUpperCase()}
        </button>
      ))}
    </div>
  );
}
