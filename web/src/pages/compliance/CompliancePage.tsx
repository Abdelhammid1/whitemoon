import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card, Spinner, InlineError } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { etaReadiness, setProductEta, type EtaReadiness } from '../../api/compliance'
import { ApiError } from '../../api/client'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'

/** Readiness KPI tile: icon chip, large mono value, label. */
function Tile({ label, value, icon, tone = 'neutral' }: { label: string; value: number; icon: string; tone?: Tone }) {
  const chip =
    tone === 'signal' ? 'bg-signal-weak text-signal'
      : tone === 'warning' ? 'bg-warning-weak text-warning'
        : tone === 'error' ? 'bg-danger-weak text-danger'
          : 'bg-brand-weak text-primary'
  return (
    <Card className="flex flex-col gap-space-md min-h-[128px]">
      <span className={`w-10 h-10 rounded-xl flex items-center justify-center ${chip}`}>
        <Icon name={icon} size={20} />
      </span>
      <div className="flex flex-col gap-0.5">
        <span className="font-mono-medium text-display tracking-tight text-on-surface" dir="ltr">{value}</span>
        <span className="font-small text-small text-secondary">{label}</span>
      </div>
    </Card>
  )
}

export function CompliancePage() {
  const toast = useToast()
  const [report, setReport] = useState<EtaReadiness | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [pid, setPid] = useState('')
  const [code, setCode] = useState('')
  const [ready, setReady] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setReport(await etaReadiness()) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function save(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await setProductEta(Number(pid), code || null, ready)
      toast.success('حُفظت جاهزية الصنف.')
      setPid(''); setCode(''); setReady(false)
      await load()
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ') }
    finally { setBusy(false) }
  }

  const allReady = report ? report.not_ready === 0 && report.total_products > 0 : false

  return (
    <Narrow>
      <div className="flex flex-wrap items-center justify-between gap-space-md">
        <PageTitle title="جاهزية الفاتورة الإلكترونية (ETA)" subtitle="كل المعاملات بالجنيه المصري. لا ربط فعلي بمصلحة الضرائب في هذا الإصدار." />
        {report && (
          allReady
            ? <Pill tone="signal">● جاهز للربط بالكامل</Pill>
            : <Pill tone="warning">● أصناف غير جاهزة</Pill>
        )}
      </div>

      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : report && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-md">
            <Tile label="إجمالي الأصناف" value={report.total_products} icon="inventory_2" />
            <Tile label="جاهزة" value={report.eta_ready} icon="verified" tone="signal" />
            <Tile label="غير جاهزة" value={report.not_ready} icon="pending_actions" tone={report.not_ready > 0 ? 'warning' : 'neutral'} />
            <Tile label="بدون كود" value={report.missing_eta_code.length} icon="error_outline" tone={report.missing_eta_code.length > 0 ? 'error' : 'neutral'} />
          </div>
        )}
      </div>

      {/* Checklist: products still missing an ETA code */}
      {report && (
        <section className="mt-space-xl">
          <Card className="flex flex-col gap-space-md">
            <div className="flex items-center justify-between pb-space-sm border-b border-surface-container-high">
              <span className="font-headline-2 text-headline-2 text-primary">قائمة أصناف بلا كود ETA</span>
              <Pill tone={report.missing_eta_code.length > 0 ? 'warning' : 'signal'}>
                {report.missing_eta_code.length} صنف
              </Pill>
            </div>
            {report.missing_eta_code.length === 0 ? (
              <div className="flex items-center gap-space-sm font-body text-body text-secondary">
                <Icon name="check_circle" size={18} className="text-signal" />
                كل الأصناف مرتبطة بكود ETA.
              </div>
            ) : (
              <ul className="flex flex-wrap gap-space-xs">
                {report.missing_eta_code.map((id) => (
                  <li key={id} className="inline-flex items-center gap-space-xs rounded-lg bg-surface-container-low px-space-sm py-1">
                    <Icon name="radio_button_unchecked" size={14} className="text-warning" />
                    <Mono className="text-secondary">#{id}</Mono>
                  </li>
                ))}
              </ul>
            )}
          </Card>
        </section>
      )}

      <section className="mt-space-xl">
        <Card className="flex flex-col gap-space-md">
          <h3 className="font-headline-2 text-headline-2 text-primary pb-space-sm border-b border-surface-container-high">ضبط كود الصنف</h3>
          <form onSubmit={save} className="flex flex-wrap items-end gap-space-md">
            <div className="w-40"><Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={pid} onChange={(e) => setPid(e.target.value)} required /></div>
            <div className="w-56"><Field label="كود الصنف (ETA)" dir="ltr" mono value={code} onChange={(e) => setCode(e.target.value)} /></div>
            <label className="flex items-center gap-space-sm font-body text-body pb-2">
              <input type="checkbox" checked={ready} onChange={(e) => setReady(e.target.checked)} /> جاهز للربط
            </label>
            <Button variant="primary" type="submit" disabled={busy || !pid}>حفظ</Button>
          </form>
          <p className="font-small text-small text-secondary">لا يمكن تعليم الصنف «جاهز» بدون كود صنف.</p>
        </Card>
      </section>
    </Narrow>
  )
}
