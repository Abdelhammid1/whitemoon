import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Spinner, Field, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { approveSupplier, listPendingSuppliers, rejectSupplier, type PendingSupplier } from '../../api/admin'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

export function PendingSuppliersPage() {
  const toast = useToast()
  const [rows, setRows] = useState<PendingSupplier[]>([])
  const [loading, setLoading] = useState(true)
  const [rejectId, setRejectId] = useState<number | null>(null)
  const [reason, setReason] = useState('')
  const [busyId, setBusyId] = useState<number | null>(null)

  async function load() {
    setLoading(true)
    try {
      setRows((await listPendingSuppliers()).items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function onApprove(id: number) {
    setBusyId(id)
    try {
      await approveSupplier(id)
      toast.success('تم اعتماد المورد.')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الاعتماد')
    } finally {
      setBusyId(null)
    }
  }

  async function onReject() {
    if (rejectId === null) return
    setBusyId(rejectId)
    try {
      await rejectSupplier(rejectId, reason)
      toast.success('تم رفض المورد مع تسجيل السبب.')
      setRejectId(null)
      setReason('')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الرفض')
    } finally {
      setBusyId(null)
    }
  }

  return (
    <Wide>
      <PageTitle title="الموردون المعلقون" subtitle="مراجعة ملفات التسجيل التجاري والوثائق الضريبية للموردين الجدد." />
      <div className="mt-space-xl flex items-center gap-space-sm">
        <Pill tone="warning">{rows.length} معلق</Pill>
      </div>

      <div className="mt-space-md">
        {loading ? (
          <Spinner />
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={rows}
              rowKey={(r) => r.user_id}
              empty="لا توجد ملفات قيد الاعتماد."
              columns={[
                { header: 'المعرف', width: '70px', cell: (r) => <Mono>{r.user_id}</Mono> },
                { header: 'الاسم القانوني', cell: (r) => <span className="font-body text-body">{r.legal_name}</span> },
                { header: 'السجل التجاري', cell: (r) => <Mono>{r.commercial_register_no}</Mono> },
                { header: 'البطاقة الضريبية', cell: (r) => <Mono>{r.tax_card_no}</Mono> },
                { header: 'تاريخ التقديم', cell: (r) => <Mono>{formatDate(r.created_at)}</Mono> },
                {
                  header: 'الإجراءات',
                  align: 'end',
                  cell: (r) => (
                    <div className="flex gap-space-sm justify-end">
                      <Button variant="primary" onClick={() => onApprove(r.user_id)} disabled={busyId === r.user_id}>اعتماد</Button>
                      <Button variant="destructive" onClick={() => setRejectId(r.user_id)} disabled={busyId === r.user_id}>رفض</Button>
                    </div>
                  ),
                },
              ]}
            />
          </Card>
        )}
      </div>

      <Modal
        open={rejectId !== null}
        onClose={() => { setRejectId(null); setReason('') }}
        title={`رفض المورد #${rejectId ?? ''}`}
        footer={
          <>
            <Button onClick={() => { setRejectId(null); setReason('') }}>إلغاء</Button>
            <Button variant="destructive" onClick={onReject} disabled={reason.trim().length < 5 || busyId === rejectId}>تأكيد الرفض</Button>
          </>
        }
      >
        <p className="font-body text-body text-secondary mb-space-md">السبب إلزامي (٥ أحرف فأكثر) ويُوثَّق في سجل التدقيق.</p>
        <Field label="سبب الرفض" value={reason} onChange={(e) => setReason(e.target.value)} />
      </Modal>
    </Wide>
  )
}
