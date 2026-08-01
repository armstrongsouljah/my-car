// Fixed, semantically-ordered expense categories — shared by the expense
// form/list (frontend/app/expenses/page.jsx) and the categorical chart
// palette (frontend/components/MonthChart.jsx).
export const CATEGORIES = [
  ["garage_visit", "Garage Visit"],
  ["modification_parts", "Modification / Parts"],
  ["fuel", "Fuel"],
  ["insurance", "Insurance"],
  ["tax_licensing", "Tax & Licensing"],
  ["cleaning", "Cleaning & Detailing"],
  ["other", "Other"],
];

export const CATEGORY_LABELS = Object.fromEntries(CATEGORIES);

// Fixed hue order (issue #58) — assigned by category identity, never
// reordered/cycled; see the CVD-validation comment above the CSS vars in
// globals.css. Literal "bg-chart-N" strings so Tailwind's JIT scanner can
// find them (a templated `bg-${var}` class name would not be generated).
export const CATEGORY_COLOR_CLASS = {
  garage_visit: "bg-chart-1",
  modification_parts: "bg-chart-2",
  fuel: "bg-chart-3",
  insurance: "bg-chart-4",
  tax_licensing: "bg-chart-5",
  cleaning: "bg-chart-6",
  other: "bg-chart-7",
};
