import { useCallback, useEffect, useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { listPeriods, periodClose, periodEnsure, periodReopen, type PeriodListRow } from '../../api/accounting'
import { ApiError } from '../../api/client'

export function PeriodsPage() {
  const toast = useToast()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState<null | 'close' | 'reopen'>(null)
  const [rows, setRows] = useState<PeriodListRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await listPeriods()
      setRows(r.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر تحميل الفترات')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  async function run(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try {
      await fn()
      toast.success(msg)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشلت العملية')
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  return (
    <Narrow>
      <PageTitle title="الفترات المالية" subtitle="إنشاء / إقفال / إعادة فتح الفترات الشهرية. إقفال الفترة يرفض أي قيد جديد عليها." />

      <section className="mt-space-xl flex flex-wrap items-end gap-space-md">
        <div className="w-28"><Field label="السنة" dir="ltr" mono value={String(year)} onChange={(e) => setYear(Number(e.target.value) || now.getFullYear())} /></div>
        <div className="w-28"><Field label="الشهر" dir="ltr" mono value={String(month)} onChange={(e) => setMonth(Number(e.target.value) || 1)} /></div>
        <Button variant="primary" onClick={() => run(() => periodEnsure(year, month), `أُنشئت الفترة ${year}/${month}`)} disabled={busy}>إنشاء / تأكيد</Button>
        <Button onClick={() => setConfirm('close')} disabled={busy}>إقفال</Button>
        <Button onClick={() => setConfirm('reopen')} disabled={busy}>إعادة فتح</Button>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="قائمة الفترات" />
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <DataTable
            rows={rows}
            rowKey={(p) => p.id}
            empty="لا توجد فترات مُنشأة بعد."
            columns={[
              { header: 'الفترة', cell: (p) => <Mono>{p.year}/{String(p.month).padStart(2, '0')}</Mono> },
              { header: 'من', cell: (p) => <Mono>{p.starts_on}</Mono> },
              { header: 'إلى', cell: (p) => <Mono>{p.ends_on}</Mono> },
              {
                header: 'الحالة',
                align: 'center',
                cell: (p) =>
                  p.is_closed ? <Pill tone="error">مُقفلة</Pill> : <Pill tone="signal">مفتوحة</Pill>,
              },
            ]}
          />
        )}
      </section>

      <Modal
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm === 'close' ? `إقفال فترة ${year}/${month}` : `إعادة فتح فترة ${year}/${month}`}
        footer={
          <>
            <Button onClick={() => setConfirm(null)}>إلغاء</Button>
            {confirm === 'close' ? (
              <Button variant="destructive" onClick={() => run(() => periodClose(year, month), `أُقفلت الفترة ${year}/${month}`)} disabled={busy}>تأكيد الإقفال</Button>
            ) : (
              <Button variant="primary" onClick={() => run(() => periodReopen(year, month), `أُعيد فتح الفترة ${year}/${month}`)} disabled={busy}>تأكيد إعادة الفتح</Button>
            )}
          </>
        }
      >
        <p className="font-body text-body text-secondary">
          {confirm === 'close'
            ? 'لن تقبل الفترة أي قيود يومية جديدة بعد الإقفال إلا عبر قيد يدوي بصلاحية خاصة.'
            : 'ستعود الفترة لاستقبال القيود. تُسجَّل العملية في سجل التدقيق.'}
        </p>
      </Modal>
    </Narrow>
  )
}
