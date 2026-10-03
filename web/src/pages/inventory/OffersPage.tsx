import { useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { myOffers, upsertOffer, type Offer } from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

export function OffersPage() {
  const toast = useToast()
  const [rows, setRows] = useState<Offer[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ product_id: '', unit_price: '', moq: '0', is_active: true })
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try { setRows((await myOffers()).items) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function onSave(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await upsertOffer({ product_id: Number(form.product_id), unit_price: form.unit_price, moq: form.moq, is_active: form.is_active })
      toast.success('تم حفظ العرض.')
      setOpen(false)
      setForm({ product_id: '', unit_price: '', moq: '0', is_active: true })
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="عروضي التوريدية" subtitle="تدير عروضك أنت فقط — لا يرى غيرك أسعارك." />
        <Button variant="primary" onClick={() => setOpen(true)} iconRight="add">إضافة / تعديل عرض</Button>
      </div>

      <div className="mt-space-xl">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(o) => o.id} empty="لا توجد عروض بعد." columns={[
            { header: 'رقم العرض', width: '90px', cell: (o) => <Mono>{o.id}</Mono> },
            { header: 'رقم المنتج', cell: (o) => <Mono>{o.product_id}</Mono> },
            { header: 'السعر', align: 'end', cell: (o) => <Mono>{formatMoney(o.unit_price)}</Mono> },
            { header: 'الحد الأدنى', align: 'end', cell: (o) => <Mono>{o.moq}</Mono> },
            { header: 'الحالة', align: 'end', cell: (o) => <Pill tone={o.is_active ? 'signal' : 'neutral'}>{o.is_active ? 'متاح' : 'موقوف'}</Pill> },
          ]} />
        )}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="إضافة / تعديل عرض" footer={
        <>
          <Button onClick={() => setOpen(false)}>إلغاء</Button>
          <Button variant="primary" onClick={onSave} disabled={busy || !form.product_id || !form.unit_price}>حفظ</Button>
        </>
      }>
        <form onSubmit={onSave} className="flex flex-col gap-space-md">
          <Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} required />
          <Field label="السعر (ج.م)" dir="ltr" mono inputMode="decimal" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} required />
          <Field label="الحد الأدنى للطلب" dir="ltr" mono inputMode="decimal" value={form.moq} onChange={(e) => setForm({ ...form, moq: e.target.value })} />
          <label className="flex items-center gap-space-sm font-body text-body">
            <input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /> متاح للبيع
          </label>
        </form>
      </Modal>
    </Wide>
  )
}
