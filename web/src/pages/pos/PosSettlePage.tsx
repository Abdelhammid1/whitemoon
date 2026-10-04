import { useCallback, useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Spinner, InlineError, SectionHeader } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { listSales, settleBatch, type PosSale, type PosBatch } from '../../api/pos'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

export function PosSettlePage() {
  const toast = useToast()
  const [unposted, setUnposted] = useState<PosSale[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [batch, setBatch] = useState<PosBatch | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setUnposted((await listSales(false)).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function settle() {
    setBusy(true)
    try { const b = await settleBatch(); setBatch(b); toast.success(`رُحِّلت ${b.sale_count} مبيعة.`); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّرت التسوية') }
    finally { setBusy(false) }
  }

  const total = unposted.reduce((s, x) => s + Number(x.total), 0)

  return (
    <Wide>
      <PageTitle title="تسوية نقطة البيع" subtitle="ترحيل دفعي للقيود المحاسبية لمبيعات نقطة البيع (مثلاً نهاية اليوم)." />
      <div className="mt-space-xl flex items-center justify-between">
        <span className="font-body text-body text-secondary">مبيعات غير مُرحَّلة: <Mono>{unposted.length}</Mono> بإجمالي <Mono>{formatMoney(total)}</Mono> ج.م</span>
        <Button variant="primary" onClick={settle} disabled={busy || unposted.length === 0}>ترحيل التسوية</Button>
      </div>
      <div className="mt-space-lg">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : (
          <DataTable rows={unposted} rowKey={(s) => s.id} empty="لا توجد مبيعات للترحيل." columns={[
            { header: 'الرقم', cell: (s) => <Mono>{s.number}</Mono> },
            { header: 'الإجمالي', align: 'end', cell: (s) => <Mono>{formatMoney(s.total)}</Mono> },
          ]} />
        )}
      </div>
      {batch && (
        <section className="mt-[48px]">
          <SectionHeader title="آخر تسوية" />
          <p className="font-body text-body text-secondary">
            دفعة #{batch.id}: <Mono>{batch.sale_count}</Mono> مبيعة بإجمالي <Mono>{formatMoney(batch.total)}</Mono> ج.م
            {batch.journal_entry_id && <> — القيد JV #{batch.journal_entry_id}</>}
          </p>
        </section>
      )}
    </Wide>
  )
}
