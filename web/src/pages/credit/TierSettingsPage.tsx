import { useEffect, useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Dot, Card, Spinner, InlineError } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { listTierSettings, setTierSetting, runEscalation, type TierSetting } from '../../api/credit'
import { ApiError } from '../../api/client'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'
const TIER_AR: Record<string, string> = { green: 'أخضر', white: 'أبيض', yellow: 'أصفر', red: 'أحمر' }
const TIER_TONE: Record<string, Tone> = { green: 'signal', white: 'neutral', yellow: 'warning', red: 'error' }

export function TierSettingsPage() {
  const toast = useToast()
  const [rows, setRows] = useState<TierSetting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState('')

  async function load() {
    setLoading(true); setError(null)
    try { setRows((await listTierSettings()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  function edit(tier: string, field: 'credit_limit' | 'deferred_pct', v: string) {
    setRows((s) => s.map((r) => (r.tier === tier ? { ...r, [field]: v } : r)))
  }
  async function save(r: TierSetting) {
    setBusy(r.tier)
    try { await setTierSetting(r.tier, r.credit_limit, r.deferred_pct); toast.success(`حُفظ تصنيف ${TIER_AR[r.tier]}.`) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ') }
    finally { setBusy('') }
  }

  return (
    <Narrow>
      <div className="flex flex-wrap items-center justify-between gap-space-md">
        <PageTitle title="سقوف التصنيف الائتماني" subtitle="عدّل السقف الافتراضي ونسبة الآجل لكل لون — يُسجَّل في التدقيق." />
        <Button onClick={async () => { const r = await runEscalation(); toast.success(`فُتح ${r.opened} تصعيد.`) }} iconRight="sync">
          تشغيل فحص التصعيد
        </Button>
      </div>
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            {rows.map((r) => {
              const tone = TIER_TONE[r.tier] ?? 'neutral'
              return (
                <Card key={r.tier} className="flex flex-col gap-space-md">
                  <div className="flex items-center justify-between pb-space-sm border-b border-surface-container-high">
                    <span className="inline-flex items-center gap-space-sm">
                      <Dot tone={tone} />
                      <span className="font-headline-2 text-headline-2 text-primary">{TIER_AR[r.tier] ?? r.tier}</span>
                    </span>
                    <Pill tone={tone}>{r.tier}</Pill>
                  </div>
                  <Field label="السقف (ج.م)" dir="ltr" mono value={r.credit_limit} onChange={(e) => edit(r.tier, 'credit_limit', e.target.value)} />
                  <Field label="الآجل %" dir="ltr" mono value={r.deferred_pct} onChange={(e) => edit(r.tier, 'deferred_pct', e.target.value)} />
                  <div className="flex justify-end">
                    <Button variant="primary" onClick={() => save(r)} disabled={busy === r.tier}>حفظ</Button>
                  </div>
                </Card>
              )
            })}
          </div>
        )}
      </div>
    </Narrow>
  )
}
