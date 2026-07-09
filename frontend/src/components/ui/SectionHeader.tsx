import type { ReactNode } from "react";

// Bold display title + optional trailing action link (the "Übersicht … Details"
// pattern used across Today / Diary / Workouts / Profile).
export function SectionHeader({
  title,
  action,
}: {
  title: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="section-header">
      <h2 className="section-header__title">{title}</h2>
      {action != null && <div className="section-header__action">{action}</div>}
    </div>
  );
}
