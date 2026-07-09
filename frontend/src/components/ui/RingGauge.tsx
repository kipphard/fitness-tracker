import type { ReactNode } from "react";

import { ringDash } from "../../lib/ring";

// Circular progress ring with centered content (the Today "remaining kcal" hero).
// `fraction` 0..1; pass `over` to flip the ring to the danger color.
export function RingGauge({
  fraction,
  label,
  sublabel,
  size = 184,
  stroke = 14,
  over = false,
}: {
  fraction: number;
  label?: ReactNode;
  sublabel?: ReactNode;
  size?: number;
  stroke?: number;
  over?: boolean;
}) {
  const radius = (size - stroke) / 2;
  const c = size / 2;
  const { circumference, offset } = ringDash(radius, fraction);
  return (
    <div className="ring-gauge" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          className="ring-gauge__track"
          cx={c}
          cy={c}
          r={radius}
          strokeWidth={stroke}
          fill="none"
        />
        <circle
          className={"ring-gauge__fill" + (over ? " is-over" : "")}
          cx={c}
          cy={c}
          r={radius}
          strokeWidth={stroke}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${c} ${c})`}
        />
      </svg>
      <div className="ring-gauge__center">
        {label != null && <span className="ring-gauge__value">{label}</span>}
        {sublabel != null && <span className="ring-gauge__label muted">{sublabel}</span>}
      </div>
    </div>
  );
}
