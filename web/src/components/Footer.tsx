/**
 * Shared "developed by" credit footer — Manasety brand.
 *
 * Ports the elyasmin `_footer.html` pattern to this React SPA. The brand
 * block is read from Vite env vars so a deployment can retitle, relabel,
 * or hide the credit without touching code:
 *
 *   VITE_BRAND_SHOW  — "0" hides the footer entirely (default: shown).
 *   VITE_BRAND_TEXT  — lead-in copy before the link (default: "Developed by").
 *   VITE_BRAND_NAME  — the clickable name (default: "Manasety").
 *   VITE_BRAND_URL   — the destination (default: https://manasety.ai).
 *
 * The anchor always opens in a new tab with `rel="noopener noreferrer"`.
 */
const APP_NAME = 'White Moon'

const brand = {
  text: (import.meta.env.VITE_BRAND_TEXT as string | undefined) ?? 'Developed by',
  name: (import.meta.env.VITE_BRAND_NAME as string | undefined) ?? 'Manasety',
  url: (import.meta.env.VITE_BRAND_URL as string | undefined) ?? 'https://manasety.ai',
  show: ((import.meta.env.VITE_BRAND_SHOW as string | undefined) ?? '1') !== '0',
}

export function Footer() {
  if (!brand.show) return null
  const year = new Date().getFullYear()
  return (
    <footer className="site-footer w-full py-space-md text-center font-small text-small text-secondary">
      <span>
        © {year} {APP_NAME} — {brand.text}{' '}
      </span>
      <a
        href={brand.url}
        target="_blank"
        rel="noopener noreferrer"
        className="brand-link font-medium text-primary hover:underline"
      >
        {brand.name}
      </a>
    </footer>
  )
}
