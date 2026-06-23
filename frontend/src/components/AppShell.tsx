import { useState } from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { useAuth } from "../auth";
import { useTheme } from "../theme";
import { ActivityExplainer } from "./explainers/ActivityExplainer";
import { FormulaExplainer } from "./explainers/FormulaExplainer";
import { BodyScreen } from "./BodyScreen";
import { DiaryScreen } from "./DiaryScreen";
import { LanguageSwitcher } from "./LanguageSwitcher";
import { PantryScreen } from "./PantryScreen";
import { ProfileScreen } from "./ProfileScreen";
import { SettingsScreen } from "./SettingsScreen";
import { ShoppingScreen } from "./ShoppingScreen";
import { TodayScreen } from "./TodayScreen";
import { TrendsScreen } from "./TrendsScreen";
import { WeightScreen } from "./WeightScreen";
import { WorkoutsScreen } from "./WorkoutsScreen";

interface NavItem {
  to: string;
  icon: string;
  key: string;
  end?: boolean;
}

// The four most-used destinations live in the mobile bottom bar; the rest go in "More".
const PRIMARY: NavItem[] = [
  { to: "/", end: true, icon: "📅", key: "today" },
  { to: "/diary", icon: "🍽️", key: "diary" },
  { to: "/workouts", icon: "🏋️", key: "workouts" },
  { to: "/trends", icon: "📈", key: "trends" },
];
const SECONDARY: NavItem[] = [
  { to: "/pantry", icon: "🥫", key: "pantry" },
  { to: "/shopping", icon: "🛒", key: "shopping" },
  { to: "/calculator", icon: "🔥", key: "calculator" },
  { to: "/weight", icon: "⚖️", key: "weight" },
  { to: "/body", icon: "📏", key: "body" },
  { to: "/formula", icon: "📐", key: "formula" },
  { to: "/activity", icon: "🏃", key: "activity" },
  { to: "/settings", icon: "⚙️", key: "settings" },
];

const linkClass = ({ isActive }: { isActive: boolean }) =>
  "sidebar__link" + (isActive ? " is-active" : "");

export function AppShell() {
  const { user, logout } = useAuth();
  const { theme, toggle } = useTheme();
  const { t } = useTranslation();
  const [moreOpen, setMoreOpen] = useState(false);

  return (
    <div className="app-shell">
      {/* Desktop sidebar */}
      <aside className="sidebar">
        <div className="sidebar__brand">💪 {t("common.appName")}</div>
        <nav className="sidebar__nav">
          {[...PRIMARY, ...SECONDARY].map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end} className={linkClass}>
              <span className="sidebar__icon">{item.icon}</span> {t(`common.nav.${item.key}`)}
            </NavLink>
          ))}
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
          <Route path="/" element={<TodayScreen />} />
          <Route path="/diary" element={<DiaryScreen />} />
          <Route path="/pantry" element={<PantryScreen />} />
          <Route path="/shopping" element={<ShoppingScreen />} />
          <Route path="/calculator" element={<ProfileScreen />} />
          <Route path="/weight" element={<WeightScreen />} />
          <Route path="/workouts" element={<WorkoutsScreen />} />
          <Route path="/trends" element={<TrendsScreen />} />
          <Route path="/body" element={<BodyScreen />} />
          <Route path="/formula" element={<FormulaExplainer />} />
          <Route path="/activity" element={<ActivityExplainer />} />
          <Route path="/settings" element={<SettingsScreen />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>

      {/* Mobile bottom tab bar */}
      <nav className="bottom-nav">
        {PRIMARY.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              "bottom-nav__item" + (isActive ? " is-active" : "")
            }
          >
            <span className="bottom-nav__icon">{item.icon}</span>
            {t(`common.nav.${item.key}`)}
          </NavLink>
        ))}
        <button
          className={"bottom-nav__item" + (moreOpen ? " is-active" : "")}
          onClick={() => setMoreOpen(true)}
        >
          <span className="bottom-nav__icon">☰</span>
          {t("common.nav.more")}
        </button>
      </nav>

      {/* Mobile "More" sheet */}
      {moreOpen && (
        <div className="more-sheet" onClick={() => setMoreOpen(false)}>
          <div className="more-sheet__panel" onClick={(e) => e.stopPropagation()}>
            <div className="more-sheet__head">
              <strong>💪 {t("common.appName")}</strong>
              <button
                className="icon-btn"
                onClick={() => setMoreOpen(false)}
                aria-label={t("diary.cancel")}
              >
                ✕
              </button>
            </div>
            {SECONDARY.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMoreOpen(false)}
                className={linkClass}
              >
                <span className="sidebar__icon">{item.icon}</span>{" "}
                {t(`common.nav.${item.key}`)}
              </NavLink>
            ))}
            <div className="more-sheet__controls">
              <LanguageSwitcher />
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
              <button
                className="btn btn--ghost btn--sm"
                onClick={() => {
                  setMoreOpen(false);
                  logout();
                }}
              >
                {t("common.logout")}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
