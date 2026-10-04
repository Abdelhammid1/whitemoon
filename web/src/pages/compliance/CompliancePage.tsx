import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Spinner, InlineError } from '../../components/ui'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { etaReadiness, setProductEta, type EtaReadiness } from '../../api/compliance'
import { ApiError } from '../../api/client'

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

  return (
    <Narrow>
      <PageTitle title="جاهزية الفاتورة الإلكترونية (ETA)" subtitle="كل المعاملات بالجنيه المصري. لا ربط فعلي بمصلحة الضرائب في هذا الإصدار." />
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : report && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-space-md">
            {[
              ['إجمالي الأصناف', report.total_products],
              ['جاهزة', report.eta_ready],
              ['غير جاهزة', report.not_ready],
              ['بدون كود', report.missing_eta_code.length],
            ].map(([k, v]) => (
              <div key={k} className="rounded-xl bg-surface-container-lowest border border-surface-container-high p-space-md flex flex-col">
                <span className="font-small text-small text-secondary">{k}</span>
                <span className="font-display text-display text-primary"><Mono>{v}</Mono></span>
              </div>
            ))}
          </div>
        )}
      </div>

      <section className="mt-[48px]">
        <h3 className="font-headline-2 text-headline-2 text-primary pb-space-sm border-b border-surface-container-high">ضبط كود الصنف</h3>
        <form onSubmit={save} className="mt-space-md flex flex-wrap items-end gap-space-md">
          <div className="w-40"><Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={pid} onChange={(e) => setPid(e.target.value)} required /></div>
          <div className="w-56"><Field label="كود الصنف (ETA)" dir="ltr" mono value={code} onChange={(e) => setCode(e.target.value)} /></div>
          <label className="flex items-center gap-space-sm font-body text-body pb-2">
            <input type="checkbox" checked={ready} onChange={(e) => setReady(e.target.checked)} /> جاهز للربط
          </label>
          <Button variant="primary" type="submit" disabled={busy || !pid}>حفظ</Button>
        </form>
        <p className="mt-space-sm font-small text-small text-secondary">لا يمكن تعليم الصنف «جاهز» بدون كود صنف.</p>
      </section>
    </Narrow>
  )
}
