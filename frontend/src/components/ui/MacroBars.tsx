export interface MacroBar {
  label: string;
  value: number;
  max: number;
  unit?: string;
}

const round = (n: number) => (Number.isFinite(n) ? Math.round(n) : 0);

// Three (or more) thin progress bars — the Today / per-meal macro breakdown.
export function MacroBars({ bars }: { bars: MacroBar[] }) {
  return (
    <div className="macro-bars">
      {bars.map((b) => {
        const pct = b.max > 0 ? Math.min(100, (b.value / b.max) * 100) : 0;
        const unit = b.unit ? ` ${b.unit}` : "";
        return (
          <div className="macro-bar" key={b.label}>
            <div className="macro-bar__head">
              <span className="macro-bar__label">{b.label}</span>
              <span className="macro-bar__val tnum">
                {round(b.value)}
                {b.max > 0 ? ` / ${round(b.max)}` : ""}
                {unit}
              </span>
            </div>
            <div className="macro-bar__track">
              <div className="macro-bar__fill" style={{ width: `${pct}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}
