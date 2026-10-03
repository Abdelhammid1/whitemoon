import { useEffect, useState } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Button } from '../../components/Button'
import { Table } from '../../components/Table'
import { Input } from '../../components/Input'
import {
  approveSupplier,
  listPendingSuppliers,
  rejectSupplier,
  type PendingSupplier,
} from '../../api/admin'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'
import { formatDate } from '../../lib/format'

export function PendingSuppliersPage() {
  const toast = useToast()
  const [rows, setRows] = useState<PendingSupplier[]>([])
  const [loading, setLoading] = useState<boolean>(true)
  const [rejectId, setRejectId] = useState<number | null>(null)
  const [reason, setReason] = useState<string>('')
  const [busyId, setBusyId] = useState<number | null>(null)

  async function load() {
    setLoading(true)
    try {
      const resp = await listPendingSuppliers()
      setRows(resp.items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

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

  async function onReject(id: number) {
    setBusyId(id)
    try {
      await rejectSupplier(id, reason)
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
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="الموردون قيد الاعتماد"
          subtitle="لا يُسمح للمورد ببيع أي شيء قبل اعتماد ملفه هنا."
        />
        {loading ? (
          <div className="text-body text-graphite">جار التحميل…</div>
        ) : (
          <Table
            rowKey={(r) => r.user_id}
            rows={rows}
            empty="لا توجد ملفات قيد الاعتماد."
            columns={[
              { header: 'المعرّف', cell: (r) => <span className="font-mono">{r.user_id}</span>, width: '80px' },
              { header: 'الاسم القانوني', cell: (r) => r.legal_name },
              { header: 'السجل التجاري', cell: (r) => <span dir="ltr">{r.commercial_register_no}</span> },
              { header: 'البطاقة الضريبية', cell: (r) => <span dir="ltr">{r.tax_card_no}</span> },
              { header: 'الرقم القومي', cell: (r) => <span dir="ltr">{r.national_id}</span> },
              { header: 'تاريخ الطلب', cell: (r) => formatDate(r.created_at) },
              {
                header: 'إجراء',
                align: 'end',
                cell: (r) => (
                  <div className="flex gap-2 justify-end">
                    <Button
                      variant="filled"
                      onClick={() => onApprove(r.user_id)}
                      disabled={busyId === r.user_id}
                    >
                      اعتماد
                    </Button>
                    <Button
                      onClick={() => setRejectId(r.user_id)}
                      disabled={busyId === r.user_id}
                    >
                      رفض
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        )}
      </Card>

      {rejectId !== null && (
        <Card>
          <CardHeader title={`رفض المورد #${rejectId}`} subtitle="السبب إلزامي (5 أحرف فأكثر)." />
          <div className="flex flex-col gap-3">
            <Input
              label="سبب الرفض"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
            />
            <div className="flex gap-2 justify-end">
              <Button onClick={() => { setRejectId(null); setReason('') }}>إلغاء</Button>
              <Button
                variant="filled"
                onClick={() => onReject(rejectId)}
                disabled={reason.trim().length < 5 || busyId === rejectId}
              >
                تأكيد الرفض
              </Button>
            </div>
          </div>
        </Card>
      )}
    </div>
  )
}
