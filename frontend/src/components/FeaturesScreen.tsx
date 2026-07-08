import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import { Card } from "./Card";

interface Feat {
  id: string;
  icon: string;
  to?: string;
  // "only" = AI required; "optional" = rule-based fallback, AI mode optional. Both off in the demo.
  ai?: "only" | "optional";
}
interface Group {
  id: string;
  items: Feat[];
}

// Adding a feature = one entry here + its name/desc/how strings in en.json & de.json.
const GROUPS: Group[] = [
  {
    id: "tracking",
    items: [
      { id: "today", icon: "📅", to: "/" },
      { id: "steps", icon: "👟", to: "/" },
    ],
  },
  {
    id: "food",
    items: [
      { id: "diary", icon: "🍽️", to: "/diary" },
      { id: "barcode", icon: "📷", to: "/diary" },
      { id: "customFood", icon: "✏️", to: "/diary" },
      { id: "mealSlots", icon: "🍱", to: "/settings" },
      { id: "copyDay", icon: "📋", to: "/diary" },
    ],
  },
  {
    id: "workouts",
    items: [
      { id: "workouts", icon: "🏋️", to: "/workouts" },
      { id: "routines", icon: "🗂️", to: "/workouts" },
      { id: "exerciseLibrary", icon: "📚", to: "/workouts" },
      { id: "progression", icon: "📈", to: "/workouts" },
      { id: "editWorkout", icon: "✏️", to: "/workouts" },
    ],
  },
  {
    id: "progress",
    items: [
      { id: "weight", icon: "⚖️", to: "/weight" },
      { id: "body", icon: "📏", to: "/body" },
      { id: "trends", icon: "📉", to: "/trends" },
    ],
  },
  {
    id: "setup",
    items: [
      { id: "calculator", icon: "🔥", to: "/calculator" },
      { id: "formula", icon: "📐", to: "/formula" },
      { id: "activity", icon: "🏃", to: "/activity" },
      { id: "settings", icon: "⚙️", to: "/settings" },
    ],
  },
  {
    id: "account",
    items: [{ id: "demo", icon: "🎮" }],
  },
];

export function FeaturesScreen() {
  const { t } = useTranslation();
  // HashRouter owns the URL hash, so jump via scrollIntoView instead of <a href="#…">.
  const jumpTo = (id: string) =>
    document.getElementById(`feat-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" });
  return (
    <div className="screen screen--prose">
      <header className="screen__head">
        <h1>{t("features.title")}</h1>
        <p className="muted">{t("features.subtitle")}</p>
      </header>

      <nav className="feature-nav" aria-label={t("features.title")}>
        {GROUPS.map((g) => (
          <button key={g.id} className="feature-nav__chip" onClick={() => jumpTo(g.id)}>
            {t(`features.groups.${g.id}`)}
          </button>
        ))}
      </nav>

      {GROUPS.map((g) => (
        <section key={g.id} id={`feat-${g.id}`} className="feature-group">
        <Card title={t(`features.groups.${g.id}`)}>
          <ul className="level-list">
            {g.items.map((f) => (
              <li key={f.id} className="level-list__item">
                <div className="level-list__head">
                  <span>
                    <strong>
                      <span aria-hidden>{f.icon}</span> {t(`features.items.${f.id}.name`)}
                    </strong>{" "}
                    {f.ai && <span className="badge">{t("features.aiBadge")}</span>}
                  </span>
                  {f.to && (
                    <Link className="btn btn--ghost btn--sm" to={f.to}>
                      {t("features.open")}
                    </Link>
                  )}
                </div>
                <p>{t(`features.items.${f.id}.desc`)}</p>
                <p className="muted">→ {t(`features.items.${f.id}.how`)}</p>
                {f.ai && (
                  <p className="muted">
                    {t(f.ai === "only" ? "features.aiOnlyNote" : "features.aiOptionalNote")}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </Card>
        </section>
      ))}
    </div>
  );
}
