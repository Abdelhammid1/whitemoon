import { useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, SectionHeader, EmptyState } from '../../components/ui'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { periodClose, periodEnsure, periodReopen } from '../../api/accounting'
import { ApiError } from '../../api/client'

export function PeriodsPage() {
  const toast = useToast()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState<null | 'close' | 'reopen'>(null)

  async function run(fn: () => Promise<unknown>, msg: string) {
    setBusy(true)
    try {
      await fn()
      toast.success(msg)
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
        <EmptyState
          title="عرض قائمة الفترات قيد الإنشاء"
          description="إجراءات الإنشاء والإقفال وإعادة الفتح تعمل الآن؛ واجهة سرد الفترات لم تُفعَّل بعد على الخادم."
        />
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
