/** @type {import('tailwindcss').Config} */

// Design-system tokens (issue #38). Backed by CSS custom properties defined
// in app/globals.css so values swap automatically with the `.dark` class
// and still support Tailwind's opacity modifiers (e.g. bg-surface-1/50).
function withOpacity(variable) {
  return `rgb(var(${variable}) / <alpha-value>)`;
}

module.exports = {
  darkMode: "class",
  content: ["./app/**/*.{js,jsx}", "./components/**/*.{js,jsx}", "./lib/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: withOpacity("--color-surface"),
          1: withOpacity("--color-surface-1"),
          2: withOpacity("--color-surface-2"),
        },
        text: {
          primary: withOpacity("--color-text-primary"),
          secondary: withOpacity("--color-text-secondary"),
          tertiary: withOpacity("--color-text-tertiary"),
          inverse: withOpacity("--color-text-inverse"),
        },
        border: {
          subtle: withOpacity("--color-border-subtle"),
          DEFAULT: withOpacity("--color-border-default"),
        },
        brand: {
          DEFAULT: withOpacity("--color-brand"),
          emphasis: withOpacity("--color-brand-emphasis"),
        },
        success: { DEFAULT: withOpacity("--color-success"), subtle: withOpacity("--color-success-subtle") },
        warning: { DEFAULT: withOpacity("--color-warning"), subtle: withOpacity("--color-warning-subtle") },
        danger: { DEFAULT: withOpacity("--color-danger"), subtle: withOpacity("--color-danger-subtle") },
        info: { DEFAULT: withOpacity("--color-info"), subtle: withOpacity("--color-info-subtle") },
      },
      fontSize: {
        display: ["28px", { lineHeight: "34px", fontWeight: "700" }],
        "title-lg": ["24px", { lineHeight: "30px", fontWeight: "700" }],
        title: ["20px", { lineHeight: "26px", fontWeight: "600" }],
        "body-lg": ["16px", { lineHeight: "24px" }],
        body: ["15px", { lineHeight: "22px" }],
        "body-sm": ["14px", { lineHeight: "20px" }],
        caption: ["13px", { lineHeight: "18px" }],
        micro: ["12px", { lineHeight: "16px" }],
      },
      boxShadow: {
        "elevation-1": "0 1px 2px rgba(0, 0, 0, 0.06), 0 1px 3px rgba(0, 0, 0, 0.08)",
        "elevation-2": "0 4px 12px rgba(0, 0, 0, 0.10), 0 2px 4px rgba(0, 0, 0, 0.06)",
        "elevation-3": "0 20px 60px rgba(0, 0, 0, 0.25), 0 8px 24px rgba(0, 0, 0, 0.12)",
      },
      transitionDuration: {
        fast: "120ms",
        base: "200ms",
        slow: "320ms",
      },
    },
  },
  plugins: [],
};
