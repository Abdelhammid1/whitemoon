/** Money and date formatting helpers. All amounts come in as strings
 *  (Decimal from the backend); we parse carefully with Intl. */

export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return String(value)
  return new Intl.NumberFormat('ar-EG', {
    style: 'currency',
    currency: 'EGP',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(n)
}

/** Bare number (Arabic-Indic, grouped, no currency, no forced decimals) —
 *  for headline KPI tiles that show the unit (ج.م) separately. */
export function formatNumber(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = typeof value === 'number' ? value : Number(value)
  if (Number.isNaN(n)) return String(value)
  return new Intl.NumberFormat('ar-EG', {
    style: 'decimal',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(n)
}

const _toArDigits = (s: string) => s.replace(/\d/g, (d) => '٠١٢٣٤٥٦٧٨٩'[Number(d)] ?? d)

/** Numeric date ٢٠٢٦/١٠/٠٥ (Arabic-Indic, Y/M/D) — renders cleanly in the mono
 *  font (digits + slashes only, no Arabic month name that mono would break). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const dt = new Date(iso)
    if (Number.isNaN(dt.getTime())) return iso
    const y = String(dt.getFullYear()).padStart(4, '0')
    const m = String(dt.getMonth() + 1).padStart(2, '0')
    const d = String(dt.getDate()).padStart(2, '0')
    return _toArDigits(`${y}/${m}/${d}`)
  } catch {
    return iso
  }
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}
