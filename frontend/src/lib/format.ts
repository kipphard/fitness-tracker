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
