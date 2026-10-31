// Formatting only: values come computed from the backend (constitution I).
export function formatBrl(value: number, locale: string): string {
  return new Intl.NumberFormat(locale, { style: "currency", currency: "BRL" }).format(value);
}

// The value is already a percentage (20 → "20%"); Intl's percent style would print "2.000%".
export function formatPercent(value: number): string {
  return `${Math.round(value)}%`;
}
