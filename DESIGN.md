---
name: White Moon
colors:
  # Canvas & surfaces (cool, navy-tinted neutrals)
  background: '#f5f7fb'
  surface: '#f5f7fb'
  surface-bright: '#ffffff'
  surface-dim: '#e2e7f1'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f0f3f9'
  surface-container: '#eef1f8'
  surface-container-high: '#e7ecf5'
  surface-container-highest: '#e2e7f1'
  surface-variant: '#e2e7f1'
  surface-tint: '#2b3a67'
  # Ink / text
  on-surface: '#1a2140'
  on-surface-variant: '#5b6480'
  on-background: '#1a2140'
  outline: '#b9c1d6'
  outline-variant: '#e2e7f1'
  inverse-surface: '#1a2140'
  inverse-on-surface: '#f2f4fa'
  # Primary = brand navy
  primary: '#2b3a67'
  on-primary: '#ffffff'
  primary-container: '#1f2a4d'
  on-primary-container: '#d6ddf2'
  inverse-primary: '#93a4e8'
  # Secondary (muted navy-grey)
  secondary: '#5b6480'
  on-secondary: '#ffffff'
  secondary-container: '#e6eaf3'
  on-secondary-container: '#424b6b'
  # Tertiary = moonlight gold (identity accent)
  tertiary: '#a8812b'
  on-tertiary: '#ffffff'
  tertiary-container: '#f3e7c8'
  on-tertiary-container: '#5a4512'
  # Semantic signals
  error: '#be3a2b'
  on-error: '#ffffff'
  error-container: '#f7d9d5'
  on-error-container: '#7a241b'
  brand: '#2b3a67'
  gold: '#a8812b'
  signal: '#16794c'
  warning: '#9c6708'
  danger: '#be3a2b'
typography:
  display:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 36px
    letterSpacing: '-0.01em'
  headline-1:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: '-0.01em'
  headline-2:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
    letterSpacing: '0'
  body:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: '0'
  body-medium:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 22px
    letterSpacing: '0'
  small:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  small-medium:
    fontFamily: IBM Plex Sans Arabic
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: '0'
  mono-body:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  mono-medium:
    fontFamily: JetBrains Mono
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 20px
    letterSpacing: '0'
rounded:
  DEFAULT: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  2xl: 1rem
  full: 9999px
shadow:
  card-sm: '0 1px 2px rgba(16,24,53,0.06)'
  card: '0 1px 2px rgba(16,24,53,0.05), 0 8px 24px -10px rgba(16,24,53,0.12)'
  overlay: '0 4px 20px -2px rgba(16,24,53,0.12), 0 2px 6px -1px rgba(16,24,53,0.08)'
spacing:
  gutter: 1rem
  margin: 1.5rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
---

## Brand & Style

White Moon ("Nightfall") is a confident, operational B2B commerce + ERP platform for the Egyptian enterprise market — a tool people run all day. The tone is premium and calm but never flat: hierarchy comes from a real brand identity, tasteful depth, and typographic rhythm, not from gray hairlines alone.

The identity is a **midnight-navy ink** paired with one restrained **moonlight-gold** accent (the crescent mark). Think Linear/Mercury density with a warm night-sky signature. Color carries structure and status; the gold is reserved for identity and the occasional highlight, never spread across surfaces.

The system is Arabic-first (`dir="rtl"`): high-register Arabic typography (IBM Plex Sans Arabic) coexists with monospaced Latin codes, ledger values, and Egyptian Pound figures (`ج.م` / `EGP`), which always render LTR inside RTL text.

## Colors

A cool, navy-tinted neutral palette on a soft off-white canvas, with a single gold identity accent and three semantic signals.

- **Canvas (`#F5F7FB`)**: the global page ground.
- **Surface (`#FFFFFF`)**: cards, panels, modals, and the sidebar.
- **Muted surface (`#EEF1F8`)**: table headers, inset wells, chips.
- **Hairline (`#E2E7F1`)**: 1px dividers and card borders.
- **Brand navy (`#2B3A67`)**: primary fills, active navigation, key headings. Darkens to `#1F2A4D` on hover. Never pure black.
- **Ink (`#1A2140`)** / **Muted (`#5B6480`)** / **Faint (`#B9C1D6`)**: text hierarchy.
- **Moonlight gold (`#A8812B`)**: identity mark and sparing highlights/accent pills only — never a large fill.

### Semantic signals (pills, dots, chart marks — not large fills)
- **Signal / success `#16794C`** — completed, active, positive.
- **Warning / hold `#9C6708`** — pending, low stock, approaching limit.
- **Critical `#BE3A2B`** — failed, rejected, frozen.

Each signal has an 8–12% soft tint token (`*-weak`) for pill backgrounds.

## Typography

- **IBM Plex Sans Arabic** — all Arabic copy, titles, labels, navigation. Weights 400 / 500 / 600 (600 now permitted for display and headings to anchor hierarchy).
- **JetBrains Mono** — all numbers, SKUs, IDs, dates, and currency (`ج.م` / `EGP`), always LTR (`dir="ltr"` / `<bdi>`); use `tabular-nums` in tables.
- Headings use `-0.01em` tracking and `text-wrap: balance`; body stays at `0`.

## Elevation & Depth

Depth is now part of the system (the previous flat, card-less rule is retired).

1. **Cards**: primary grouping device — `#FFFFFF` on the canvas, 1px `#E2E7F1` border, `1rem` (16px) radius, `shadow-card`. Use them for KPI tiles, panels, list groups, and the sidebar.
2. **Hairlines**: still used for table rows and in-card dividers (`1px #E2E7F1`), no background shift.
3. **Overlays**: modals and slide-overs use `shadow-overlay` over a navy-tinted blurred backdrop (`rgba(16,24,53,0.28)`, `blur(4px)`).
4. **Hover lift**: interactive cards raise from `shadow-card` to `shadow-overlay` on hover.

## Shapes

- **Controls (buttons, inputs)**: `0.5rem` (8px) radius.
- **Cards & panels**: `1rem` (16px) radius.
- **Modals / sheets**: `0.75rem` (12px) radius.
- **Pills / badges**: fully rounded (`9999px`).
- **Table cells & dividers**: square.

## Components

### Brand
- Gold crescent glyph (`text-gold`) beside the bilingual wordmark **وايت مون / White Moon** in `headline-2`.

### Buttons
- **Primary**: solid navy `#2B3A67`, white text, `shadow-card-sm`, hover `#1F2A4D`.
- **Secondary**: white, 1px `#E2E7F1` border, navy text, hover muted surface.
- **Destructive**: white, 1px border, `#BE3A2B` text.

### Inputs
- Bottom-border underline: `1px #E7ECF5` baseline → `2px #2B3A67` on focus. Transparent background, faint placeholder. Error state uses `danger`.

### Navigation (sidebar)
- White card rail. Items are rounded; the active item is a filled navy pill with white text and `shadow-card-sm`; inactive items hover to a muted surface. Counts appear as small gold pills.

### Status pills
- `20px` micro-badges, fully rounded, `13px` JetBrains Mono. Tones: `signal`, `warning`, `error`, `gold`, `brand`, `neutral` — each a soft tint background with the matching ink.

### Data tables / ledgers
- No outer border. Header row on muted surface with a hairline bottom rule. Arabic content right-aligned; mono numbers/currency/timestamps left-aligned with `tabular-nums`. Hairline row dividers, no zebra.

### Cards & KPI tiles
- KPI tile: label, a large mono value, a trend delta pill (signal/warning/error), and an optional sparkline. Charts are drawn to scale with readable Arabic labels and a gold-highlighted latest point.

## Layout & Spacing

Centered content: `760px` for reading/forms, up to `1040px` for dense tables and dashboards. Gutters `1rem` mobile → `1.5rem` desktop. Spacing steps: 4 / 8 / 12 / 16 / 24 / 32 / 48 / 64 px. Group with flex/grid `gap`, not per-element margins.
