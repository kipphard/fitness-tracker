import type { ReactNode } from "react";

// Big tappable selectable card (onboarding steps + goal/gender/activity pickers).
// `multi` renders a checkbox affordance (square) instead of a radio (round).
export function OptionCard({
  selected,
  onSelect,
  label,
  description,
  icon,
  multi = false,
  disabled = false,
}: {
  selected: boolean;
  onSelect: () => void;
  label: ReactNode;
  description?: ReactNode;
  icon?: ReactNode;
  multi?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      className={"option-card" + (selected ? " is-selected" : "")}
      onClick={onSelect}
      disabled={disabled}
      role={multi ? "checkbox" : "radio"}
      aria-checked={selected}
    >
      {icon != null && (
        <span className="option-card__icon" aria-hidden>
          {icon}
        </span>
      )}
      <span className="option-card__text">
        <span className="option-card__label">{label}</span>
        {description != null && <span className="option-card__desc muted">{description}</span>}
      </span>
      <span
        className={"option-card__mark" + (multi ? " option-card__mark--multi" : "")}
        aria-hidden
      >
        {selected ? "✓" : ""}
      </span>
    </button>
  );
}
