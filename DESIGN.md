---
name: White Moon
colors:
  surface: '#fbf9f9'
  surface-dim: '#dbdad9'
  surface-bright: '#fbf9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f3'
  surface-container: '#efeded'
  surface-container-high: '#e9e8e7'
  surface-container-highest: '#e4e2e2'
  on-surface: '#1b1c1c'
  on-surface-variant: '#444748'
  inverse-surface: '#303031'
  inverse-on-surface: '#f2f0f0'
  outline: '#747878'
  outline-variant: '#c4c7c7'
  surface-tint: '#5f5e5e'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#1c1b1b'
  on-primary-container: '#858383'
  inverse-primary: '#c8c6c5'
  secondary: '#5d5f5f'
  on-secondary: '#ffffff'
  secondary-container: '#dfe0e0'
  on-secondary-container: '#616363'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#1d1b1a'
  on-tertiary-container: '#868381'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e5e2e1'
  primary-fixed-dim: '#c8c6c5'
  on-primary-fixed: '#1c1b1b'
  on-primary-fixed-variant: '#474646'
  secondary-fixed: '#e2e2e2'
  secondary-fixed-dim: '#c6c6c7'
  on-secondary-fixed: '#1a1c1c'
  on-secondary-fixed-variant: '#454747'
  tertiary-fixed: '#e6e1df'
  tertiary-fixed-dim: '#cac6c3'
  on-tertiary-fixed: '#1d1b1a'
  on-tertiary-fixed-variant: '#484645'
  background: '#fbf9f9'
  on-background: '#1b1c1c'
  surface-variant: '#e4e2e2'
typography:
  display:
    fontFamily: IBM Plex Sans
    fontSize: 28px
    fontWeight: '500'
    lineHeight: 36px
    letterSpacing: '0'
  headline-1:
    fontFamily: IBM Plex Sans
    fontSize: 20px
    fontWeight: '500'
    lineHeight: 28px
    letterSpacing: '0'
  headline-2:
    fontFamily: IBM Plex Sans
    fontSize: 16px
    fontWeight: '500'
    lineHeight: 24px
    letterSpacing: '0'
  body:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 22px
    letterSpacing: '0'
  body-medium:
    fontFamily: IBM Plex Sans
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 22px
    letterSpacing: '0'
  small:
    fontFamily: IBM Plex Sans
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 20px
    letterSpacing: '0'
  small-medium:
    fontFamily: IBM Plex Sans
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
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
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

This design system delivers an austere, high-density, utility-driven B2B commerce and enterprise resource platform tailored specifically for the Egyptian enterprise ecosystem. The emotional tone is authoritative, quiet, and friction-free—eschewing ornamentation, decorative containers, and heavy surfaces in favor of rapid legibility and editorial rhythm. 

The aesthetic operates at the intersection of high-modernist Swiss typography and contemporary functionalist engineering (evoking Linear, Vercel, and Mercury). Rather than segregating information inside heavy cards and drop shadows, layout hierarchy is communicated purely through precise whitespace, typographic cadence, hairline rules, and high-contrast ink values.

The system is architected as Arabic-first (`dir="rtl"`), natively handling bidirectional script demands where high-register Arabic typography seamlessly coexists with monospaced Latin technical codes, ledger values, and Egyptian Pound (`ج.م` / `EGP`) financial figures.

## Colors

The system uses a strictly light-mode, reductive palette. Color is never decorative; it exists solely as structure, typography, or binary status signals.

### Palette Architecture
- **Canvas Base (`#FFFFFF`)**: The global base surface for all pages, sheets, and active panels.
- **Muted Surface (`#FAFAFA`)**: Applied selectively to table headers, utility bars, and subtle state toggles.
- **Hairline Border (`#EBEBEB`)**: Used with extreme discipline—strictly 1px rules for dividing sections and table ledgers. Never used to frame isolated cards.
- **Primary Ink (`#111111`)**: Dominant near-black used for headers, primary body text, active state indicators, and primary action fills.
- **Muted Text (`#6E6E6E`)**: Secondary labels, non-active metadata, and supporting documentation.
- **Faint Text (`#A1A1A1`)**: Disabled text, structural hints, and inactive trailing glyphs.

### Semantic Signals (Badges & Indicators Only)
Signal colors are restricted strictly to micro-pills, badges, and inline status dots. They must never tint large backgrounds or card surfaces:
- **Signal / Active (`#0F6B3E`)**: Completed transactions, active vendor accounts, positive net variance.
- **Warning / Hold (`#A8650C`)**: Pending clearances, customs verification, low warehouse stock.
- **Error / Critical (`#B3261E`)**: Failed settlements, rejected KYC submissions, cancellation alerts.

## Typography

The typographic hierarchy relies on pure scale, restraint, and deliberate dual-font pairings:
- **IBM Plex Sans (Arabic variant)**: Governs all Arabic narrative copy, titles, structural labels, and navigation.
- **JetBrains Mono**: Exclusively allocated to numeric entries, SKU references, tracking IDs, dates, and currency values (`EGP` / `ج.م`). All numerical strings render LTR even within RTL sentences.

### Rules of Engagement
- **Weights**: Restrict to `400` (Regular) and `500` (Medium). Weights of `600` or above are strictly prohibited to maintain an airy, understated character.
- **Letter Spacing**: Maintained at exactly `0` across all scales and fonts.
- **Bidirectional Alignment**: In RTL views, text defaults to right-aligned. Whenever numbers, tax registration identifiers, or SKU codes appear, wrap them in inline direction-isolated tags (`<bdi>` or `dir="ltr"`) rendered in JetBrains Mono to avoid punctuation skew.

## Layout & Spacing

Layouts reject excessive dashboard nesting and multiple side-by-side containers. Instead, the interface adopts a focused, column-based document layout.

### Grid & Max-Width Philosophy
- Primary operational views, detail records, and configuration panels sit within a single, centered content column ranging between `760px` (reading, forms, settings) and `1040px` (dense inventory tables and analytics logs).
- Canvas gutters scale from `1rem` on mobile breakpoints to `1.5rem` on desktop.

### Spatial Rhythm
The spacing system uses a defined step scale:
- `4px` (`0.25rem`): Micro gaps between paired inline metadata, tags, and icons.
- `8px` (`0.5rem`): Internal element gaps, badge padding, and vertical label-to-input clearance.
- `12px` (`0.75rem`): Row-level component padding in dense lists.
- `16px` (`1rem`): Standard operational gutter and component spacing.
- `24px` (`1.5rem`): Section gaps between interrelated data groups.
- `32px` (`2rem`): Major category transitions.
- `48px` (`3rem`), `64px` (`4rem`), `96px` (`6rem`): Macro vertical canvas separation.

## Elevation & Depth

This design system is virtually non-elevated. Traditional surface-container stacking, drop shadows, and border-encased cards are eliminated.

### Rules of Depth
1. **Zero Shadow Baseline**: Primary and secondary canvas spaces exist on a flat plane. Cards are not permitted; groupings are defined by 1px bottom borders (`#EBEBEB`) or vertical spacing steps (`32px` to `48px`).
2. **Hairline Delimiters**: When spatial isolation is structurally required (e.g., separating summary data or table headers), a single `1px solid #EBEBEB` rule is used without background elevation shifts.
3. **Transient Overlays**: Modals, slide-over command sheets, and dropdown menus utilize an isolated, crisp drop shadow to detach from the active canvas:
   `box-shadow: 0 4px 20px -2px rgba(17, 17, 17, 0.06), 0 2px 6px -1px rgba(17, 17, 17, 0.04);`
   Modals sit atop a muted backdrop: `rgba(255, 255, 255, 0.8)` with backdrop filter `blur(4px)`.

## Shapes

The geometric personality is sharp and disciplined, reflecting industrial precision:
- **Interactive Controls (Buttons, Inputs)**: `6px` border-radius (`0.375rem`), creating a clean, architectural silhouette.
- **Sheets & Modals**: `8px` border-radius (`0.5rem`).
- **Status Badges & Indicator Pills**: Fully rounded `999px` (`rounded-full`) to immediately delineate status metadata from interactive rectangles.
- **Tables, Cell Dividers, Dividers**: Square, zero-radius (`0px`).

## Components

### Brand Identity & Glyph
- The identity mark pairs a minimal crescent moon glyph (`☽` or custom geometric SVG) alongside the bilingual brand mark **وايت مون / White Moon** rendered in `headline-2` (`500` weight).

### Buttons
- **Primary**: Solid `#111111` fill, `#FFFFFF` text, `6px` border radius, `14px` Medium typography. No borders, no shadows.
- **Secondary**: `#FFFFFF` background, `1px solid #EBEBEB`, `#111111` text. On hover, background shifts to `#FAFAFA`.
- **Destructive**: `#FFFFFF` background, `1px solid #EBEBEB`, `#B3261E` text. Hover shifts to `#FAFAFA`.

### Input Fields & Controls
- **Text Inputs**: Minimal bottom-border underline inputs. No 4-sided containment box. The baseline is `1px solid #EBEBEB`, transitioning smoothly to `1px solid #111111` on focus. Background is transparent. Placeholder text uses text-faint (`#A1A1A1`).
- **Checkboxes & Radios**: `16px` squared (`4px` radius for checkbox) with a `1px solid #EBEBEB` rim. Selected state fills with `#111111` and an `#FFFFFF` icon mark.

### Status Pills
- Micro badges (`20px` height) with `999px` radius, padding `2px 8px`, using `13px` JetBrains Mono for status counters or bilingual codes.
- Signal pill: Background `rgba(15, 107, 62, 0.08)`, text `#0F6B3E`.
- Warning pill: Background `rgba(168, 101, 12, 0.08)`, text `#A8650C`.
- Error pill: Background `rgba(179, 38, 30, 0.08)`, text `#B3261E`.

### Data Tables & Ledgers
- Tables discard outer wrapper borders. Header row sits on `#FAFAFA` with bottom border `1px solid #EBEBEB`, labels in `13px` `text-muted` (`#6E6E6E`).
- Data rows feature `14px` Arabic content right-aligned, and `13px` JetBrains Mono numbers, currency amounts (`ج.م`), and timestamps left-aligned. Each row concludes with a hairline `1px solid #EBEBEB` divider. No zebra striping.

### Modals & Dialogs
- Maximum width of `540px`, centered, background `#FFFFFF`, bordered by `1px solid #EBEBEB` with `8px` corner radius. Header and footer actions separated by hairline dividers.