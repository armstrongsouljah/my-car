# GlavBox design system

Reference for `frontend/`. Establishes tokens and rules for new work going forward — it does **not** retrofit existing pages/components (that's a separate follow-up issue). Tokens live in [`frontend/tailwind.config.js`](../frontend/tailwind.config.js) (`theme.extend`) and [`frontend/app/globals.css`](../frontend/app/globals.css) (`:root` / `.dark` custom properties).

## Principles

Act as a principal Apple design director would: extreme clarity, deep typographic hierarchy, precise 8pt-grid layout, deliberate whitespace, and fluid, physics-based micro-interactions. Every screen should read as calm and functional before it reads as decorated.

## Color strategy

Two deliberately separate palettes:

- **App chrome** (dashboard, forms, lists, cards, settings — everything reached after login) stays **neutral gray/slate** in both light and dark mode. This is the lowest-risk choice and matches how the codebase already treats the two surfaces differently.
- **Brand moments** (`/login`, the marketing landing page, transactional emails) keep the existing dark-green (`#04120c`/`#0a1a14`) + emerald (`#34d399`) brand-locked look, independent of the light/dark app theme. Nothing here changes that — see `.auth-input`/`.auth-label` in `globals.css` and `frontend/app/login/page.jsx`.
- **Emerald is the one accent color** used across the *entire* app regardless of surface: primary buttons, links, active nav/tab state, and focus rings. It's the thread that ties neutral app chrome back to the brand.

### Tokens

| Token | CSS var | Light | Dark | Usage |
|---|---|---|---|---|
| `surface` | `--color-surface` | `#ffffff` | `#030712` | Page background |
| `surface-1` | `--color-surface-1` | `#ffffff` | `#111827` | Card / panel background |
| `surface-2` | `--color-surface-2` | `#f9fafb` | `#1f2937` | Raised surface (modal, popover, floating nav) |
| `text-primary` | `--color-text-primary` | `#111827` | `#f3f4f6` | Headings, primary body text |
| `text-secondary` | `--color-text-secondary` | `#4b5563` | `#9ca3af` | Secondary text, labels |
| `text-tertiary` | `--color-text-tertiary` | `#9ca3af` | `#6b7280` | Placeholder, disabled, hints |
| `text-inverse` | `--color-text-inverse` | `#ffffff` | `#111827` | Text on a filled `brand`/`text-primary` background |
| `border-subtle` | `--color-border-subtle` | `#e5e7eb` | `#1f2937` | Hairlines, dividers |
| `border-default` | `--color-border-default` | `#d1d5db` | `#374151` | Input/card borders |
| `brand` | `--color-brand` | `#10b981` | `#34d399` | Primary accent — buttons, links, active states, focus rings |
| `brand-emphasis` | `--color-brand-emphasis` | `#059669` | `#10b981` | Hover/pressed variant of `brand` |
| `success` / `success-subtle` | `--color-success*` | `#15803d` / `#dcfce7` | `#4ade80` / solid dark wash | "OK" status |
| `warning` / `warning-subtle` | `--color-warning*` | `#b45309` / `#fef3c7` | `#fbbf24` / solid dark wash | "Due soon" status |
| `danger` / `danger-subtle` | `--color-danger*` | `#b91c1c` / `#fee2e2` | `#f87171` / solid dark wash | "Overdue" / error status |
| `info` / `info-subtle` | `--color-info*` | `#1d4ed8` / `#dbeafe` | `#60a5fa` / solid dark wash | Informational callouts |

Usage: `bg-surface-1 text-text-primary border border-border-default`, `bg-brand text-text-inverse`, `bg-danger-subtle text-danger`. Opacity modifiers work as usual (`bg-surface-1/50`).

The `success`/`warning`/`danger`/`info` pair formalizes the ad hoc pattern already used in `StatusChip.jsx` (`bg-{c}-100 text-{c}-700` light / `dark:bg-{c}-500/15 dark:text-{c}-400` dark) into named tokens.

## Typography

Named scale in `tailwind.config.js` → `theme.extend.fontSize`. Use these instead of arbitrary pixel values (`text-[15px]`, `text-[13px]`, etc.) in new code.

| Class | Size / line-height | Weight | Use for |
|---|---|---|---|
| `text-display` | 28px / 34px | 700 | Rare hero/landing headlines |
| `text-title-lg` | 24px / 30px | 700 | Page-level headers (e.g. dashboard `h1`) |
| `text-title` | 20px / 26px | 600 | Section headers, card titles |
| `text-body-lg` | 16px / 24px | — | Emphasized body copy |
| `text-body` | 15px / 22px | — | Default body/UI text (today's de facto default) |
| `text-body-sm` | 14px / 20px | — | Secondary/supporting text |
| `text-caption` | 13px / 18px | — | Form labels, metadata |
| `text-micro` | 12px / 16px | — | Chips, badges, timestamps |

Pair with `font-medium`/`font-semibold`/`font-bold` as needed — weight is intentionally not baked into the smaller sizes.

## Spacing — 8pt grid

Tailwind's default spacing scale is 4px-based and already covers the grid: use steps `1` (4px), `2` (8px), `3` (12px), `4` (16px), `6` (24px), `8` (32px), `10` (40px), `12` (48px), `16` (64px). Stick to these — avoid arbitrary values like `py-3.5` (14px, off-grid; present today in `.auth-input`) or one-off `px-[Npx]` classes. Existing off-grid spots are left as-is for the retrofit issue, not fixed here.

## Radius & elevation

No new Tailwind config keys — the existing default radius scale already maps cleanly onto a semantic system, so just apply it consistently:

| Semantic role | Class | Px |
|---|---|---|
| Inputs, buttons | `rounded-xl` | 12px |
| Cards, sheets | `rounded-2xl` | 16px |
| Pills, avatars, floating nav | `rounded-full` | — |

Elevation (`theme.extend.boxShadow`) replaces the inconsistent bare `shadow`/`shadow-sm`/`shadow-lg` mix:

| Class | Use for |
|---|---|
| `shadow-elevation-1` | Cards resting on the page |
| `shadow-elevation-2` | Floating elements (FAB, floating nav, dropdowns) |
| `shadow-elevation-3` | Modals, sheets, anything above a scrim |

## Component states

Every interactive component should define these states explicitly. `focus-visible` is called out separately because **no component in the codebase currently has one** — this is the accessibility gap this system exists to close going forward.

| Component | Default | Active (pressed) | Focus-visible | Disabled | Loading |
|---|---|---|---|---|---|
| Button (primary) | `bg-brand text-text-inverse` | `active:scale-[0.98]` | `focus-visible:ring-2 focus-visible:ring-brand focus-visible:ring-offset-2 focus-visible:ring-offset-surface` | `disabled:opacity-50 disabled:pointer-events-none` | spinner replaces label, button stays same size |
| Button (secondary) | `border border-border-default bg-surface-1 text-text-primary` | `active:scale-[0.98]` | same ring recipe | `disabled:opacity-50` | same pattern |
| Input | `border border-border-default bg-surface-1 text-text-primary` | `focus:border-brand` | `focus-visible:ring-2 focus-visible:ring-brand/50` | `disabled:opacity-50 disabled:bg-surface-2` | n/a |
| Card | `bg-surface-1 border border-border-subtle shadow-elevation-1` | `active:scale-[0.99]` (only if the whole card is tappable) | ring on the card itself if it's a link/button | — | skeleton/shimmer placeholder, same footprint |
| Nav item | `text-text-tertiary` | selected state: `text-brand` (or filled pill per `BottomNav.jsx`'s existing pattern) | `focus-visible:ring-2 focus-visible:ring-brand` | n/a | n/a |

## Motion

`theme.extend.transitionDuration`:

| Token | Duration | Use for |
|---|---|---|
| `duration-fast` | 120ms | Tap/press feedback |
| `duration-base` | 200ms | Default transitions (hover, color/opacity changes) |
| `duration-slow` | 320ms | Sheets, modals, larger layout shifts |

- Standardize tap feedback on **`active:scale-[0.98]`** (today's code mixes `0.99` and `0.95` — pick `0.98` going forward).
- Default easing is Tailwind's `ease-out` for anything entering the screen; no custom easing curve needed beyond that.
- Respect `prefers-reduced-motion`: wrap non-essential scale/transform animations so they no-op under `@media (prefers-reduced-motion: reduce)` when introducing new motion-heavy components.

## Accessibility baseline

- **Contrast**: WCAG AA — 4.5:1 for body text, 3:1 for large text (≥18px/24px bold) and UI components (borders, icons conveying state).
- **Focus-visible**: every interactive element must show the `focus-visible:ring-2 focus-visible:ring-brand` treatment above. This is currently missing app-wide — required for all new components.
- **Touch targets**: minimum 44×44px hit area for anything tappable, even if the visible glyph is smaller (pad with padding/pseudo-elements, not by inflating the icon).
- **Motion**: honor `prefers-reduced-motion` (see Motion section).
- **Alt text / labels**: images need `alt`; icon-only buttons need `aria-label`.

## Adoption

This issue only establishes the system — it does not change any existing page's rendering. `frontend/tailwind.config.js` and `globals.css` changes here are additive (new tokens only; no existing `@layer components` class was modified). Applying these tokens to existing components (`StatusChip`, `BottomNav`, `.card`/`.btn-primary`/`.input`, etc.) is scoped to a separate follow-up issue.
