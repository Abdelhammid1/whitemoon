/** @type {import('tailwindcss').Config}
 *  Theme ported verbatim from the Stitch export (white_moon design system).
 *  Font stacks extended to put the Arabic variant first so RTL copy renders
 *  in IBM Plex Sans Arabic and numerals/codes in JetBrains Mono.
 */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // ── White Moon "Nightfall" system ──────────────────────────────
        // Midnight-navy ink, cool neutrals, one restrained moonlight-gold
        // accent. Token names kept from the Stitch export so pages re-skin.
        // Canvas & surfaces
        background: '#f5f7fb',
        surface: '#f5f7fb',
        'surface-bright': '#ffffff',
        'surface-dim': '#e2e7f1',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#f0f3f9',
        'surface-container': '#eef1f8',
        'surface-container-high': '#e7ecf5',
        'surface-container-highest': '#e2e7f1',
        'surface-variant': '#e2e7f1',
        'surface-tint': '#2b3a67',
        // Ink / text
        'on-surface': '#1a2140',
        'on-background': '#1a2140',
        'on-surface-variant': '#5b6480',
        outline: '#b9c1d6',
        'outline-variant': '#e2e7f1',
        // Primary = brand navy
        primary: '#2b3a67',
        'on-primary': '#ffffff',
        'primary-container': '#1f2a4d',
        'on-primary-container': '#d6ddf2',
        'primary-fixed': '#dfe4f3',
        'primary-fixed-dim': '#aab4d8',
        'on-primary-fixed': '#141b35',
        'on-primary-fixed-variant': '#3a4672',
        // Secondary (muted navy-grey)
        secondary: '#5b6480',
        'on-secondary': '#ffffff',
        'secondary-container': '#e6eaf3',
        'on-secondary-container': '#424b6b',
        'secondary-fixed': '#e6eaf3',
        'secondary-fixed-dim': '#c6cde0',
        'on-secondary-fixed': '#141b35',
        'on-secondary-fixed-variant': '#424b6b',
        // Tertiary = moonlight gold (accent / identity)
        tertiary: '#a8812b',
        'on-tertiary': '#ffffff',
        'tertiary-container': '#f3e7c8',
        'on-tertiary-container': '#5a4512',
        'tertiary-fixed': '#f3e7c8',
        'tertiary-fixed-dim': '#e0c88a',
        'on-tertiary-fixed': '#3b2d08',
        'on-tertiary-fixed-variant': '#6f550f',
        // Inverse (dark surfaces / tooltips)
        'inverse-surface': '#1a2140',
        'inverse-on-surface': '#f2f4fa',
        'inverse-primary': '#93a4e8',
        // Error
        error: '#be3a2b',
        'on-error': '#ffffff',
        'error-container': '#f7d9d5',
        'on-error-container': '#7a241b',
        // Brand + semantic signals (+ soft tints for pills/badges)
        brand: '#2b3a67',
        'brand-weak': 'rgba(43,58,103,0.08)',
        gold: '#a8812b',
        'gold-weak': 'rgba(168,129,43,0.12)',
        signal: '#16794c',
        'signal-weak': 'rgba(22,121,76,0.10)',
        warning: '#9c6708',
        'warning-weak': 'rgba(156,103,8,0.12)',
        danger: '#be3a2b',
        'danger-weak': 'rgba(190,58,43,0.10)',
      },
      borderRadius: {
        DEFAULT: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
        '2xl': '1rem',
        full: '1rem',
        pill: '9999px',
      },
      boxShadow: {
        card: '0 1px 2px rgba(16,24,53,0.05), 0 8px 24px -10px rgba(16,24,53,0.12)',
        'card-sm': '0 1px 2px rgba(16,24,53,0.06)',
        overlay: '0 4px 20px -2px rgba(16,24,53,0.12), 0 2px 6px -1px rgba(16,24,53,0.08)',
      },
      spacing: {
        margin: '1.5rem',
        'space-sm': '0.5rem',
        'space-md': '1rem',
        gutter: '1rem',
        'space-xs': '0.25rem',
        'space-xl': '2rem',
        'space-lg': '1.5rem',
      },
      fontFamily: {
        'small-medium': ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
        body: ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
        'body-medium': ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
        // Exact mono stack from the approved design mockup — Arabic-Indic
        // digits fall through to the OS monospace (Consolas on Windows), so
        // numbers render identically to the mockup.
        'mono-medium': ['JetBrains Mono', 'ui-monospace', 'Cascadia Mono', 'monospace'],
        'mono-body': ['JetBrains Mono', 'ui-monospace', 'Cascadia Mono', 'monospace'],
        'headline-1': ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
        display: ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
        'headline-2': ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
        small: ['IBM Plex Sans Arabic', 'IBM Plex Sans', 'sans-serif'],
      },
      fontSize: {
        'small-medium': ['13px', { lineHeight: '20px', letterSpacing: '0', fontWeight: '500' }],
        body: ['14px', { lineHeight: '22px', letterSpacing: '0', fontWeight: '400' }],
        'body-medium': ['14px', { lineHeight: '22px', letterSpacing: '0', fontWeight: '500' }],
        'mono-medium': ['13px', { lineHeight: '20px', letterSpacing: '0', fontWeight: '500' }],
        'mono-body': ['13px', { lineHeight: '20px', letterSpacing: '0', fontWeight: '400' }],
        'headline-1': ['20px', { lineHeight: '28px', letterSpacing: '0', fontWeight: '500' }],
        display: ['28px', { lineHeight: '36px', letterSpacing: '0', fontWeight: '500' }],
        'headline-2': ['16px', { lineHeight: '24px', letterSpacing: '0', fontWeight: '500' }],
        small: ['13px', { lineHeight: '20px', letterSpacing: '0', fontWeight: '400' }],
      },
    },
  },
  plugins: [],
}
