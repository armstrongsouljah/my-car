// Mirrors api/utils/Constants.py's CURRENCY_CHOICES — keep the two in sync.
export const CURRENCIES = [
  ["UGX", "Ugandan Shilling (UGX)"],
  ["KES", "Kenyan Shilling (KES)"],
  ["TZS", "Tanzanian Shilling (TZS)"],
  ["RWF", "Rwandan Franc (RWF)"],
  ["NGN", "Nigerian Naira (NGN)"],
  ["GHS", "Ghanaian Cedi (GHS)"],
  ["ZAR", "South African Rand (ZAR)"],
  ["EGP", "Egyptian Pound (EGP)"],
  ["USD", "US Dollar (USD)"],
  ["GBP", "British Pound (GBP)"],
  ["EUR", "Euro (EUR)"],
  ["INR", "Indian Rupee (INR)"],
  ["AED", "UAE Dirham (AED)"],
  ["CAD", "Canadian Dollar (CAD)"],
  ["AUD", "Australian Dollar (AUD)"],
];

// See #40 — client-side formatting so every screen that renders money can
// react instantly to a currency change without a server round trip. Falls
// back to a bare, symbol-less number (today's pre-#40 behavior) when the
// user has no currency set, or when the stored code isn't one
// Intl.NumberFormat recognizes.
export function formatAmount(amount, currencyCode) {
  const value = Number(amount) || 0;
  if (!currencyCode) return value.toLocaleString();
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency: currencyCode }).format(value);
  } catch {
    return value.toLocaleString();
  }
}

// See #125 — for figures printed directly on/above a chart bar, where a
// currency with a large everyday nominal amount (UGX, TZS, NGN, ...)
// otherwise renders wider than the bar itself. 10,000 -> "10k", 1,000,000
// -> "1m", and so on. Intl's own `notation: "compact"` does the rounding/
// suffix math (and stays locale-correct for symbol placement); it just
// defaults to an uppercase suffix (e.g. "10K"), so the trailing letter is
// lowercased to match this app's own convention.
export function formatAmountCompact(amount, currencyCode) {
  const value = Number(amount) || 0;
  const options = { notation: "compact", maximumFractionDigits: 1 };
  try {
    if (!currencyCode) throw new Error("no currency code");
    return new Intl.NumberFormat(undefined, { ...options, style: "currency", currency: currencyCode })
      .format(value)
      .replace(/([KMB])$/, (letter) => letter.toLowerCase());
  } catch {
    return new Intl.NumberFormat(undefined, options).format(value).replace(/([KMB])$/, (letter) => letter.toLowerCase());
  }
}
