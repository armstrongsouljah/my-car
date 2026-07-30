// Mirrors api/utils/Constants.py's COUNTRY_CHOICES — keep the two in sync;
// a code missing here just can't be picked, same as one missing there just
// leaves currency undefaulted (see #40).
export const COUNTRIES = [
  ["AT", "Austria"],
  ["AU", "Australia"],
  ["AE", "United Arab Emirates"],
  ["BE", "Belgium"],
  ["CA", "Canada"],
  ["DE", "Germany"],
  ["EG", "Egypt"],
  ["ES", "Spain"],
  ["FI", "Finland"],
  ["FR", "France"],
  ["GB", "United Kingdom"],
  ["GH", "Ghana"],
  ["IE", "Ireland"],
  ["IN", "India"],
  ["IT", "Italy"],
  ["KE", "Kenya"],
  ["NG", "Nigeria"],
  ["NL", "Netherlands"],
  ["PT", "Portugal"],
  ["RW", "Rwanda"],
  ["TZ", "Tanzania"],
  ["UG", "Uganda"],
  ["US", "United States"],
  ["ZA", "South Africa"],
];

// ISO 3166-1 alpha-2 -> flag emoji, built from the Unicode regional
// indicator symbols (0x1F1E6 sits 127397 code points above 'A').
export function flagEmoji(countryCode) {
  if (!countryCode || countryCode.length !== 2) return "";
  return [...countryCode.toUpperCase()]
    .map((char) => String.fromCodePoint(127397 + char.charCodeAt(0)))
    .join("");
}
