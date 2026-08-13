// Ports frontend/lib/currency.js's formatAmount -- see #40. Falls back to a
// bare, symbol-less number when the user has no currency set, or when the
// stored code isn't one Intl.NumberFormat recognizes.
export function formatAmount(amount: number, currencyCode?: string | null) {
  const value = Number(amount) || 0;
  if (!currencyCode) return value.toLocaleString();
  try {
    return new Intl.NumberFormat(undefined, { style: 'currency', currency: currencyCode }).format(value);
  } catch {
    return value.toLocaleString();
  }
}
