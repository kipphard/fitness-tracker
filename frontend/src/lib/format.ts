export function num(value: string | number | null | undefined): number {
  if (value == null || value === "") return 0;
  const n = typeof value === "number" ? value : Number(value);
  return Number.isFinite(n) ? n : 0;
}

// Parse a user-typed decimal that may use a comma (de locale) or a dot into a dot-decimal
// string safe for the API (which parses Decimal). Returns "" when it isn't a finite number,
// so callers can treat empty/invalid the same way.
export function parseDecimalInput(value: string): string {
  const norm = value.trim().replace(",", ".");
  if (norm === "") return "";
  return Number.isFinite(Number(norm)) ? norm : "";
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

const CURRENCY_SYMBOLS: Record<string, string> = { EUR: "€", USD: "$", GBP: "£" };

export function currencySymbol(currency?: string | null): string {
  const code = currency || "EUR";
  return CURRENCY_SYMBOLS[code] ?? `${code} `;
}

// Money display, e.g. "€12.50". Decimals arrive as strings from the API.
export function money(value: string | number | null | undefined, currency?: string | null): string {
  return `${currencySymbol(currency)}${num(value).toFixed(2)}`;
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
