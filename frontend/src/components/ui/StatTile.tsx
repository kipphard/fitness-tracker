import type { ReactNode } from "react";

// Compact stat card (2-up grids on Today / Profile): big value + label.
export function StatTile({
  value,
  label,
  icon,
}: {
  value: ReactNode;
  label: ReactNode;
  icon?: ReactNode;
}) {
  return (
    <div className="stat-tile">
      {icon != null && <span className="stat-tile__icon">{icon}</span>}
      <span className="stat-tile__value tnum">{value}</span>
      <span className="stat-tile__label muted">{label}</span>
    </div>
  );
}
