import { useEffect, useMemo, useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Dot, Card, Spinner, InlineError, SectionHeader } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  getDeferredSettings, updateDeferredSettings, setDeferredTierRate, setDeferredException,
  deleteDeferredException, reviewDeferredSettings, type DeferredSettings,
} from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'
const TIER_AR: Record<string, string> = { green: 'أخضر', white: 'أبيض', yellow: 'أصفر', red: 'أحمر' }
const TIER_TONE: Record<string, Tone> = { green: 'signal', white: 'neutral', yellow: 'warning', red: 'error' }
const TIER_ORDER = ['green', 'white', 'yellow', 'red']

/** Live fee example: amount × annual% / 365 × days, 2 dp. */
function exampleFee(amount: number, annualPct: number, days: number): number {
  return Math.round((amount * (annualPct / 100) / 365 * days) * 100) / 100
}

export function DeferredSettingsPage() {
  const toast = useToast()
  const [data, setData] = useState<DeferredSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState('')

  // editable copies
  const [general, setGeneral] = useState('')
  const [defaultDays, setDefaultDays] = useState('')
  const [maxDays, setMaxDays] = useState('')
  const [allowedDays, setAllowedDays] = useState('')
  const [tierRates, setTierRates] = useState<Record<string, string>>({})

  // exception form
  const [excCid, setExcCid] = useState('')
  const [excPct, setExcPct] = useState('')
  const [excReason, setExcReason] = useState('')

  // live example
  const [exAmount, setExAmount] = useState('10000')
  const [exDays, setExDays] = useState('15')

  function hydrate(d: DeferredSettings) {
    setData(d)
    setGeneral(d.annual_pct_general)
    setDefaultDays(String(d.default_days))
    setMaxDays(String(d.max_days))
    setAllowedDays(d.allowed_days.join('، '))
    setTierRates(Object.fromEntries(TIER_ORDER.map((t) => [t, d.tier_rates[t] ?? ''])))
  }

  async function load() {
    setLoading(true); setError(null)
    try { hydrate(await getDeferredSettings()) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  function parseDays(s: string): number[] {
    return [...new Set(s.split(/[،,\s]+/).map((x) => Number(x.trim())).filter((n) => Number.isFinite(n) && n > 0))]
  }

  async function run(key: string, fn: () => Promise<DeferredSettings>, msg: string) {
    setBusy(key)
    try { hydrate(await fn()); toast.success(msg) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّرت العملية') }
    finally { setBusy('') }
  }

  const exampleRate = Number(general) || 0
  const exampleValue = useMemo(
    () => exampleFee(Number(exAmount) || 0, exampleRate, Number(exDays) || 0),
    [exAmount, exampleRate, exDays],
  )

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error || !data) return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير متاح'} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title="إعدادات البيع الآجل" subtitle="النسبة السنوية والمدد المتاحة والاستثناءات — القيم تُطبَّق على الطلبات الجديدة فقط." />
      <PageHelp pageKey="deferred-settings" />

      {!data.reviewed && (
        <Card className="mt-space-lg border-r-4 border-warning bg-warning/5 flex items-center justify-between gap-space-md">
          <span className="font-body text-body text-on-surface">قيم مقترحة لم تُراجع بعد — راجعها واعتمدها قبل التشغيل.</span>
          <Button variant="primary" disabled={busy === 'review'}
            onClick={() => void run('review', reviewDeferredSettings, 'تم اعتماد القيم.')}>اعتماد القيم</Button>
        </Card>
      )}

      {/* General + durations */}
      <section className="mt-space-xl">
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title="النسبة العامة والمدد" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="النسبة السنوية العامة %" dir="ltr" mono value={general} onChange={(e) => setGeneral(e.target.value)} />
            <Field label="المدة الافتراضية (يوم)" dir="ltr" mono inputMode="numeric" value={defaultDays} onChange={(e) => setDefaultDays(e.target.value)} />
            <Field label="أقصى مدة (يوم)" dir="ltr" mono inputMode="numeric" value={maxDays} onChange={(e) => setMaxDays(e.target.value)} />
            <Field label="المدد المسموح بها (يوم)" dir="ltr" mono value={allowedDays} onChange={(e) => setAllowedDays(e.target.value)} hint="افصل بينها بفاصلة" />
          </div>
          <div className="flex justify-end">
            <Button variant="primary" disabled={busy === 'general'}
              onClick={() => void run('general', () => updateDeferredSettings({
                annual_pct_general: general,
                default_days: Number(defaultDays),
                max_days: Number(maxDays),
                allowed_days: parseDays(allowedDays),
              }), 'حُفظت الإعدادات.')}>حفظ</Button>
          </div>
        </Card>
      </section>

      {/* Live example */}
      <section className="mt-space-lg">
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title="مثال حيّ" />
          <div className="flex flex-wrap items-end gap-space-md">
            <div className="w-40"><Field label="قيمة الطلب (ج.م)" dir="ltr" mono value={exAmount} onChange={(e) => setExAmount(e.target.value)} /></div>
            <div className="w-32"><Field label="المدة (يوم)" dir="ltr" mono value={exDays} onChange={(e) => setExDays(e.target.value)} /></div>
          </div>
          <p className="font-body text-body text-on-surface">
            طلب <bdi dir="ltr">{formatMoney(exAmount || '0')}</bdi> × {exDays || 0} يوم × {exampleRate}% ÷ 365 ={' '}
            رسوم <bdi dir="ltr">{formatMoney(String(exampleValue))}</bdi>، الإجمالي{' '}
            <bdi dir="ltr">{formatMoney(String((Number(exAmount) || 0) + exampleValue))}</bdi>
          </p>
        </Card>
      </section>

      {/* Per-tier rates */}
      <section className="mt-space-lg">
        <SectionHeader title="نسب حسب التصنيف (تتجاوز العامة)" />
        <div className="mt-space-md grid grid-cols-1 sm:grid-cols-2 gap-space-md">
          {TIER_ORDER.map((t) => {
            const tone = TIER_TONE[t] ?? 'neutral'
            return (
              <Card key={t} className="flex flex-col gap-space-sm">
                <div className="flex items-center justify-between">
                  <span className="inline-flex items-center gap-space-sm"><Dot tone={tone} /><span className="font-body-medium text-body">{TIER_AR[t]}</span></span>
                  {t === 'red' && <Pill tone="error">لا يُسمح بالآجل</Pill>}
                </div>
                <div className="flex items-end gap-space-sm">
                  <div className="flex-1">
                    <Field label="النسبة السنوية %" dir="ltr" mono value={tierRates[t] ?? ''}
                      hint="اترِكها فارغة لاستخدام العامة"
                      onChange={(e) => setTierRates((s) => ({ ...s, [t]: e.target.value }))} />
                  </div>
                  <Button disabled={busy === `tier-${t}`}
                    onClick={() => void run(`tier-${t}`, () => setDeferredTierRate(t, tierRates[t]?.trim() ? tierRates[t] : null), `حُفظ تصنيف ${TIER_AR[t]}.`)}>حفظ</Button>
                </div>
              </Card>
            )
          })}
        </div>
      </section>

      {/* Per-customer exceptions */}
      <section className="mt-space-lg">
        <SectionHeader title="استثناءات حسب العميل" />
        <Card className="mt-space-md flex flex-col gap-space-md">
          <div className="flex flex-wrap items-end gap-space-md">
            <div className="w-32"><Field label="رقم العميل" dir="ltr" mono inputMode="numeric" value={excCid} onChange={(e) => setExcCid(e.target.value)} /></div>
            <div className="w-32"><Field label="النسبة %" dir="ltr" mono value={excPct} onChange={(e) => setExcPct(e.target.value)} /></div>
            <div className="flex-1 min-w-[200px]"><Field label="السبب" value={excReason} onChange={(e) => setExcReason(e.target.value)} /></div>
            <Button variant="primary" disabled={busy === 'exc' || !excCid || !excPct || excReason.trim().length < 5}
              onClick={() => void run('exc', () => setDeferredException(Number(excCid), excPct, excReason.trim()), 'أُضيف الاستثناء.')
                .then(() => { setExcCid(''); setExcPct(''); setExcReason('') })}>إضافة استثناء</Button>
          </div>
          {data.exceptions.length > 0 && (
            <DataTable rows={data.exceptions} rowKey={(r) => r.customer_id} columns={[
              { header: 'العميل', cell: (r) => <Mono>{r.customer_id}</Mono> },
              { header: 'النسبة', align: 'end', cell: (r) => <Mono>{r.annual_pct}%</Mono> },
              { header: 'السبب', cell: (r) => <span className="text-secondary">{r.reason}</span> },
              {
                header: '', align: 'end',
                cell: (r) => (
                  <button className="text-danger font-small-medium hover:underline disabled:opacity-40" disabled={busy === `del-${r.customer_id}`}
                    onClick={() => void run(`del-${r.customer_id}`, () => deleteDeferredException(r.customer_id), 'حُذف الاستثناء.')}>حذف</button>
                ),
              },
            ]} />
          )}
        </Card>
      </section>
    </Narrow>
  )
}
