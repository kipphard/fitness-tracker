export function num(value: string | number | null | undefined): number {
  if (value == null || value === "") return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

// Whole-kcal display (the engine returns exact Decimals; we round for the UI).
export function kcal(value: string | number | null | undefined): string {
  return Math.round(num(value)).toLocaleString();
}

export function oneDecimal(value: string | number | null | undefined): string {
  return num(value).toLocaleString(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 3,
  });
}

export function shortDate(value?: string | null): string {
  if (!value) return "—";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "—" : d.toLocaleDateString();
}

// Today's *local* calendar date as YYYY-MM-DD (not UTC — toISOString would shift
// across midnight for users east/west of UTC).
export function todayIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(
    d.getDate(),
  ).padStart(2, "0")}`;
}

// Add n days to a YYYY-MM-DD string. Parse and format in UTC so the result never
// drifts by the local timezone offset (the bug that broke the diary's prev/next).
export function addDays(iso: string, n: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
