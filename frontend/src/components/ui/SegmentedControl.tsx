import type { ReactNode } from "react";

export interface Segment<T extends string> {
  value: T;
  label: ReactNode;
}

// Pill segmented toggle (tabs like Volumen/Wdh/Dauer, Ich/Freunde). Generalizes
// the existing language-switcher pattern.
export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  block = false,
}: {
  options: Segment<T>[];
  value: T;
  onChange: (value: T) => void;
  block?: boolean;
}) {
  return (
    <div className={"segmented" + (block ? " segmented--block" : "")} role="tablist">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="tab"
          aria-selected={o.value === value}
          className={"segmented__btn" + (o.value === value ? " is-active" : "")}
          onClick={() => onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
