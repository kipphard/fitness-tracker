import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth";
import { useTheme } from "../theme";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { ProfileScreen } from "./ProfileScreen";
import { SettingsScreen } from "./SettingsScreen";
import { FormulaExplainer } from "./explainers/FormulaExplainer";
import { ActivityExplainer } from "./explainers/ActivityExplainer";

const linkClass = ({ isActive }: { isActive: boolean }) =>
  "sidebar__link" + (isActive ? " is-active" : "");

export function AppShell() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { t } = useTranslation();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar__brand">💪 {t("common.appName")}</div>
        <nav className="sidebar__nav">
          <NavLink to="/" end className={linkClass}>
            <span className="sidebar__icon">🔥</span> {t("common.nav.calculator")}
          </NavLink>
          <NavLink to="/formula" className={linkClass}>
            <span className="sidebar__icon">📐</span> {t("common.nav.formula")}
          </NavLink>
          <NavLink to="/activity" className={linkClass}>
            <span className="sidebar__icon">🏃</span> {t("common.nav.activity")}
          </NavLink>
          <NavLink to="/settings" className={linkClass}>
            <span className="sidebar__icon">⚙️</span> {t("common.nav.settings")}
          </NavLink>
        </nav>
        <div className="sidebar__footer">
          <LanguageSwitcher />
          <div className="sidebar__footer-row">
            <button
              className="icon-btn"
              onClick={toggle}
              aria-label={t("common.toggleTheme")}
              title={t("common.toggleTheme")}
            >
              {theme === "light" ? "🌙" : "☀️"}
            </button>
            <span className="muted sidebar__email" title={user?.email}>
              {user?.email}
            </span>
          </div>
          <button className="btn btn--ghost btn--sm" onClick={logout}>
            {t("common.logout")}
          </button>
        </div>
      </aside>

      <main className="app-main">
        <Routes>
          <Route path="/" element={<ProfileScreen />} />
          <Route path="/formula" element={<FormulaExplainer />} />
          <Route path="/activity" element={<ActivityExplainer />} />
          <Route path="/settings" element={<SettingsScreen />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
