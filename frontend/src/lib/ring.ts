// Geometry for a circular SVG progress ring. `fraction` is clamped to [0,1] for
// the visual arc (values > 1, e.g. over-target, render as a full ring).
export function ringDash(radius: number, fraction: number): {
  circumference: number;
  offset: number;
} {
  const circumference = 2 * Math.PI * radius;
  const f = Number.isFinite(fraction) ? Math.max(0, Math.min(1, fraction)) : 0;
  return { circumference, offset: circumference * (1 - f) };
}
