import { useState } from "react";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth";

// Shown at the top of the app while in a demo sandbox. Dismissible for the session.
export function DemoBanner() {
  const { user } = useAuth();
  const { t } = useTranslation();
  const [dismissed, setDismissed] = useState(
    () => sessionStorage.getItem("fit_demo_banner") === "1",
  );
  if (!user?.is_demo || dismissed) return null;
  return (
    <div className="demo-banner">
      <span>
        {t("demo.banner")} ·{" "}
        <a href="https://kipphard.com" target="_blank" rel="noreferrer">
          {t("demo.builtBy")}
        </a>
      </span>
      <button
        className="icon-btn"
        aria-label={t("demo.dismiss")}
        onClick={() => {
          sessionStorage.setItem("fit_demo_banner", "1");
          setDismissed(true);
        }}
      >
        ✕
      </button>
    </div>
  );
}
