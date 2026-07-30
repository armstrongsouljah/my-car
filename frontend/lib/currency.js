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
