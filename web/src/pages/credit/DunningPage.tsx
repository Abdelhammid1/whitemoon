import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card, Spinner, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { listDunning, listTierSettings, runEscalation, type DunningRow } from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'
const TIER_TONE: Record<string, Tone> = { green: 'signal', white: 'neutral', yellow: 'warning', red: 'error' }
const TIER_AR: Record<string, string> = { green: 'أخضر', white: 'أبيض', yellow: 'أصفر', red: 'أحمر' }
// Graceful fallback used only until the backend tier list loads (or if it fails);
// always carries a leading '' ("الكل") option.
const FALLBACK_TIERS = ['', 'white', 'green', 'yellow', 'red']
const BAR: Record<Tone, string> = { signal: 'bg-signal', warning: 'bg-warning', error: 'bg-danger', neutral: 'bg-primary/55' }

/** Distribution of the overdue customers currently shown, by credit tier.
 *  Purely a read-only view over the already-loaded rows. */
function TierDistribution({ rows }: { rows: DunningRow[] }) {
  const counts = rows.reduce<Record<string, number>>((acc, r) => {
    acc[r.tier] = (acc[r.tier] ?? 0) + 1
    return acc
  }, {})
  const entries = (['red', 'yellow', 'white', 'green'] as const)
    .map((t) => [t, counts[t] ?? 0] as const)
    .filter(([, n]) => n > 0)
  const max = entries.reduce((m, [, n]) => Math.max(m, n), 0) || 1
  return (
    <Card className="flex flex-col">
      <div className="flex items-center justify-between pb-space-sm mb-space-md border-b border-surface-container-high">
        <span className="font-headline-2 text-headline-2 text-on-surface">توزيع التصنيف للمتأخرين</span>
        <span className="font-mono-medium text-mono-medium text-secondary" dir="ltr">{rows.length}</span>
      </div>
      <div className="flex flex-col gap-space-sm">
        {entries.map(([t, n]) => {
          const tone = TIER_TONE[t] ?? 'neutral'
          return (
            <div key={t} className="flex flex-col gap-1">
              <div className="flex items-center justify-between font-small text-small">
                <span className="text-secondary">{TIER_AR[t]}</span>
                <span className="font-mono-body text-on-surface" dir="ltr">{n}</span>
              </div>
              <div className="h-1.5 rounded-pill bg-surface-container overflow-hidden">
                <div className={`h-full rounded-pill ${BAR[tone]}`} style={{ width: `${Math.max(4, (n / max) * 100)}%` }} />
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}

export function DunningPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [rows, setRows] = useState<DunningRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [minDays, setMinDays] = useState('')
  const [tier, setTier] = useState('')
  const [tiers, setTiers] = useState<string[]>(FALLBACK_TIERS)

  // Tier codes are loaded from the backend tier settings; falls back to the seed
  // on failure. The leading '' ("الكل") option is always kept.
  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const { items } = await listTierSettings()
        if (alive && items.length) setTiers(['', ...items.map((i) => i.tier)])
      } catch {
        /* keep FALLBACK_TIERS */
      }
    })()
    return () => { alive = false }
  }, [])

  const load = useCallback(async (opts?: { min_days?: number; tier?: string }) => {
    setLoading(true); setError(null)
    try {
      const { items } = await listDunning({
        min_days: opts?.min_days,
        tier: opts?.tier || undefined,
      })
      setRows(items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  function apply(nextTier = tier) {
    void load({ min_days: minDays ? Number(minDays) : undefined, tier: nextTier })
  }

  async function runScan() {
    setBusy(true)
    try {
      const { opened } = await runEscalation()
      toast.success(`فُتح ${opened} تصعيد.`)
      apply()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل التشغيل')
    } finally {
      setBusy(false)
    }
  }

  function chip(active: boolean) {
    return `px-3 py-1 rounded-pill font-small transition-colors ${active ? 'bg-primary text-on-primary shadow-card-sm' : 'bg-surface-variant text-on-surface-variant hover:bg-surface-container-high'}`
  }

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle title="المتابعة والتحصيل" subtitle="العملاء ذوو الذمم المتأخرة، الأسوأ أولاً. كل القيم بالجنيه المصري." />
        <Button variant="primary" disabled={busy} onClick={runScan} iconRight="sync">تشغيل فحص التصعيد</Button>
      </div>

      <PageHelp pageKey="dunning" />

      {/* Filters */}
      <div className="mt-space-lg flex flex-wrap items-end gap-space-md">
        <div className="flex gap-space-xs pb-2">
          {tiers.map((t) => (
            <button key={t || 'all'} type="button" className={chip(tier === t)} onClick={() => { setTier(t); apply(t) }}>
              {t === '' ? 'الكل' : TIER_AR[t]}
            </button>
          ))}
        </div>
        <div className="w-32"><Field label="أدنى أيام تأخر" dir="ltr" mono value={minDays} inputMode="numeric" onChange={(e) => setMinDays(e.target.value)} /></div>
        <Button disabled={loading} onClick={() => apply()}>تطبيق</Button>
      </div>

      {!loading && !error && rows.length > 0 && (
        <div className="mt-space-lg">
          <TierDistribution rows={rows} />
        </div>
      )}

      <div className="mt-space-lg">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <Card padded={false} className="overflow-hidden">
          <DataTable
            rows={rows}
            rowKey={(r) => r.customer_id}
            onRowClick={() => navigate('/credit')}
            empty={<EmptyState title="لا توجد ذمم متأخرة." />}
            columns={[
              {
                header: 'العميل',
                cell: (r) => (
                  <div className="flex flex-col">
                    <span className="font-body-medium text-body-medium text-on-surface">{r.display_name ?? '—'}</span>
                    <Mono className="text-secondary">#{r.customer_id}</Mono>
                  </div>
                ),
              },
              { header: 'التصنيف', align: 'center', cell: (r) => <Pill tone={TIER_TONE[r.tier] ?? 'neutral'}>{TIER_AR[r.tier] ?? r.tier}</Pill> },
              { header: 'المستحق', align: 'end', cell: (r) => <span dir="ltr"><Mono>{formatMoney(r.outstanding)}</Mono> ج.م</span> },
              { header: 'عدد الذمم', align: 'center', cell: (r) => <Mono>{r.open_due_count}</Mono> },
              { header: 'أسوأ تأخر', align: 'end', cell: (r) => <span dir="ltr"><Mono>{r.worst_overdue_days}</Mono> يوم</span> },
              {
                header: 'الحالة',
                align: 'center',
                cell: (r) =>
                  r.order_block_level >= 4 ? (
                    <Pill tone="error">تجميد كل الطلبات</Pill>
                  ) : r.order_block_level >= 2 ? (
                    <Pill tone="warning">حظر الآجل + خفض السقف</Pill>
                  ) : (
                    <span className="text-secondary">—</span>
                  ),
              },
            ]}
          />
          </Card>
        )}
      </div>
    </Wide>
  )
}
