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

/** Hint for date-column headers: every date/time on the platform is shown in
 *  Cairo time, never the viewer's own timezone (T-34). Put on a column's
 *  `title`/tooltip so «ليه التاريخ مختلف عن توقيتي؟» answers itself. */
export const CAIRO_TZ_HINT = 'التوقيت بتوقيت القاهرة'

/** Numeric date ٠٥/١٠/٢٠٢٦ (Arabic-Indic, **dd/mm/yyyy**, Cairo time) — renders
 *  cleanly in the mono font (digits + slashes only). Cairo-fixed so the day
 *  never drifts for a viewer in another timezone (T-34). */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const dt = new Date(iso)
    if (Number.isNaN(dt.getTime())) return iso
    const p = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Africa/Cairo',
      year: 'numeric', month: '2-digit', day: '2-digit',
    }).formatToParts(dt)
    const g = (t: string) => p.find((x) => x.type === t)?.value ?? ''
    return _toArDigits(`${g('day')}/${g('month')}/${g('year')}`)
  } catch {
    return iso
  }
}

/** Date + time (hour:minute) in Egypt time (Africa/Cairo), Arabic-Indic digits,
 *  **dd/mm/yyyy hh:mm**, e.g. ٠٧/١٠/٢٠٢٦ ١٤:٣٢ — regardless of the viewer's own
 *  timezone (T-34). Use for every operation timestamp. */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  try {
    const dt = new Date(iso)
    if (Number.isNaN(dt.getTime())) return iso
    const p = new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Africa/Cairo',
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(dt)
    const g = (t: string) => p.find((x) => x.type === t)?.value ?? ''
    return _toArDigits(`${g('day')}/${g('month')}/${g('year')} ${g('hour')}:${g('minute')}`)
  } catch {
    return iso
  }
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}
