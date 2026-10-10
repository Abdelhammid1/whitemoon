import { useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  supplierProducts, setSupplierProduct, createCodingRequest, type SupplierProduct,
} from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

const selectCls =
  'bg-transparent border-b border-surface-container-high py-2 font-body text-body focus:outline-none focus:border-primary w-full'

type EditForm = {
  product_id: string
  unit_price: string
  on_hand: string
  moq: string
  is_active: boolean
  discount_kind: 'none' | 'percent' | 'price'
  discount_value: string
  discount_start: string
  discount_end: string
}
const EMPTY: EditForm = {
  product_id: '', unit_price: '', on_hand: '0', moq: '0', is_active: true,
  discount_kind: 'none', discount_value: '', discount_start: '', discount_end: '',
}

export function SupplierProductsPage() {
  const toast = useToast()
  const [rows, setRows] = useState<SupplierProduct[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [edit, setEdit] = useState<EditForm | null>(null)
  const [adding, setAdding] = useState(false)
  const [coding, setCoding] = useState<null | { name: string; barcode: string; brand: string; category: string; note: string }>(null)

  async function load() {
    setLoading(true)
    try { setRows((await supplierProducts()).items) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function openEdit(p: SupplierProduct) {
    setAdding(false)
    setEdit({
      product_id: String(p.product_id),
      unit_price: p.offer ? String(Number(p.offer.unit_price)) : '',
      on_hand: String(Number(p.on_hand)),
      moq: p.offer ? String(Number(p.offer.moq)) : '0',
      is_active: p.offer ? p.offer.is_active : true,
      discount_kind: p.offer?.discount_kind ?? 'none',
      discount_value: p.offer?.discount_value ? String(Number(p.offer.discount_value)) : '',
      discount_start: p.offer?.discount_start ?? '',
      discount_end: p.offer?.discount_end ?? '',
    })
  }
  function openAdd() { setAdding(true); setEdit({ ...EMPTY }) }

  async function save(e: FormEvent) {
    e.preventDefault()
    if (!edit) return
    setBusy(true)
    try {
      await setSupplierProduct(Number(edit.product_id), {
        unit_price: edit.unit_price,
        on_hand: edit.on_hand,
        moq: edit.moq,
        is_active: edit.is_active,
        discount_kind: edit.discount_kind,
        discount_value: edit.discount_kind === 'none' ? null : edit.discount_value,
        discount_start: edit.discount_kind === 'none' || !edit.discount_start ? null : edit.discount_start,
        discount_end: edit.discount_kind === 'none' || !edit.discount_end ? null : edit.discount_end,
      })
      toast.success('تم حفظ المنتج.')
      setEdit(null)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally { setBusy(false) }
  }

  async function submitCoding(e: FormEvent) {
    e.preventDefault()
    if (!coding) return
    setBusy(true)
    try {
      await createCodingRequest({
        name: coding.name, barcode: coding.barcode || undefined, brand: coding.brand || undefined,
        category: coding.category || undefined, note: coding.note || undefined,
      })
      toast.success('أُرسل طلب التكويد للمراجعة.')
      setCoding(null)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إرسال الطلب')
    } finally { setBusy(false) }
  }

  return (
    <Wide>
      <div className="flex flex-wrap items-start justify-between gap-space-sm">
        <PageTitle title="منتجاتي" subtitle="السعر والكمية والخصم في شاشة واحدة — خصمك يجب أن يحقق أفضل سعر على المنصة." />
        <div className="flex gap-space-sm">
          <Button onClick={() => setCoding({ name: '', barcode: '', brand: '', category: '', note: '' })} iconRight="note_add">اطلب تكويد صنف</Button>
          <Button variant="primary" onClick={openAdd} iconRight="add">إضافة منتج</Button>
        </div>
      </div>

      <PageHelp pageKey="supplier-products" />

      <Card padded={false} className="mt-space-xl overflow-hidden">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(p) => p.product_id} empty="لا توجد منتجات بعد — أضف منتجًا أو اطلب تكويد صنف." columns={[
            {
              header: 'المنتج',
              cell: (p) => (
                <span className="flex items-center gap-space-sm">
                  {p.image_url ? <img src={p.image_url} alt="" className="w-9 h-9 rounded-md object-cover" /> : <span className="w-9 h-9 rounded-md bg-surface-container" />}
                  <span className="flex flex-col">
                    <span className="font-body-medium text-body-medium text-primary">{p.name}</span>
                    {p.barcode && <span className="font-mono-body text-small text-secondary" dir="ltr">{p.barcode}</span>}
                  </span>
                </span>
              ),
            },
            { header: 'السعر', align: 'end', cell: (p) => <Mono>{p.offer ? formatMoney(p.offer.unit_price) : '—'}</Mono> },
            {
              header: 'الخصم', align: 'center',
              cell: (p) => p.offer && p.offer.discount_kind !== 'none'
                ? <Pill tone="signal">{formatMoney(p.offer.effective_price)}</Pill>
                : <span className="text-secondary">—</span>,
            },
            { header: 'المخزون', align: 'end', cell: (p) => <Mono>{Number(p.on_hand)}</Mono> },
            { header: 'الحالة', align: 'center', cell: (p) => <Pill tone={p.offer?.is_active ? 'signal' : 'neutral'}>{p.offer?.is_active ? 'متاح' : (p.offer ? 'موقوف' : 'بدون عرض')}</Pill> },
            { header: '', align: 'end', cell: (p) => <button className="text-primary font-small-medium hover:underline" onClick={() => openEdit(p)}>تعديل</button> },
          ]} />
        )}
      </Card>

      {/* Edit / add product */}
      <Modal open={edit !== null} onClose={() => setEdit(null)} title={adding ? 'إضافة منتج' : 'تعديل المنتج'} footer={
        <>
          <Button onClick={() => setEdit(null)}>إلغاء</Button>
          <Button variant="primary" onClick={save} disabled={busy || !edit?.product_id || !edit?.unit_price}>حفظ</Button>
        </>
      }>
        {edit && (
          <form onSubmit={save} className="flex flex-col gap-space-md">
            {adding && (
              <Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={edit.product_id}
                onChange={(e) => setEdit({ ...edit, product_id: e.target.value })} required
                hint="رقم المنتج من الكتالوج — أو اطلب تكويد صنف جديد" />
            )}
            <div className="grid grid-cols-2 gap-space-md">
              <Field label="السعر (ج.م)" dir="ltr" mono inputMode="decimal" value={edit.unit_price} onChange={(e) => setEdit({ ...edit, unit_price: e.target.value })} required />
              <Field label="الكمية المتاحة" dir="ltr" mono inputMode="decimal" value={edit.on_hand} onChange={(e) => setEdit({ ...edit, on_hand: e.target.value })} />
              <Field label="الحد الأدنى للطلب" dir="ltr" mono inputMode="decimal" value={edit.moq} onChange={(e) => setEdit({ ...edit, moq: e.target.value })} />
              <label className="flex items-center gap-space-sm font-body text-body self-end">
                <input type="checkbox" checked={edit.is_active} onChange={(e) => setEdit({ ...edit, is_active: e.target.checked })} /> متاح للبيع
              </label>
            </div>
            <div className="flex flex-col gap-1">
              <span className="font-small text-small text-secondary">الخصم</span>
              <select className={selectCls} value={edit.discount_kind} onChange={(e) => setEdit({ ...edit, discount_kind: e.target.value as EditForm['discount_kind'] })}>
                <option value="none">بدون خصم</option>
                <option value="percent">نسبة مئوية %</option>
                <option value="price">سعر مخفّض مباشر</option>
              </select>
            </div>
            {edit.discount_kind !== 'none' && (
              <>
                <Field label={edit.discount_kind === 'percent' ? 'نسبة الخصم %' : 'السعر بعد الخصم (ج.م)'} dir="ltr" mono inputMode="decimal"
                  value={edit.discount_value} onChange={(e) => setEdit({ ...edit, discount_value: e.target.value })} required />
                <div className="grid grid-cols-2 gap-space-md">
                  <Field label="بداية الخصم" type="date" dir="ltr" mono value={edit.discount_start} onChange={(e) => setEdit({ ...edit, discount_start: e.target.value })} />
                  <Field label="نهاية الخصم" type="date" dir="ltr" mono value={edit.discount_end} onChange={(e) => setEdit({ ...edit, discount_end: e.target.value })} />
                </div>
                <p className="font-small text-small text-secondary">يُقبل الخصم فقط إذا حقّق أفضل سعر على المنصة؛ وإلا يُرفض دون كشف سعر المنافس.</p>
              </>
            )}
          </form>
        )}
      </Modal>

      {/* Request coding */}
      <Modal open={coding !== null} onClose={() => setCoding(null)} title="طلب تكويد صنف" footer={
        <>
          <Button onClick={() => setCoding(null)}>إلغاء</Button>
          <Button variant="primary" onClick={submitCoding} disabled={busy || !coding?.name.trim()}>إرسال</Button>
        </>
      }>
        {coding && (
          <form onSubmit={submitCoding} className="flex flex-col gap-space-md">
            <Field label="اسم الصنف" value={coding.name} onChange={(e) => setCoding({ ...coding, name: e.target.value })} required />
            <div className="grid grid-cols-2 gap-space-md">
              <Field label="الباركود (اختياري)" dir="ltr" mono value={coding.barcode} onChange={(e) => setCoding({ ...coding, barcode: e.target.value })} />
              <Field label="العلامة التجارية (اختياري)" value={coding.brand} onChange={(e) => setCoding({ ...coding, brand: e.target.value })} />
            </div>
            <Field label="الفئة (اختياري)" value={coding.category} onChange={(e) => setCoding({ ...coding, category: e.target.value })} />
            <Field label="ملاحظة (اختياري)" value={coding.note} onChange={(e) => setCoding({ ...coding, note: e.target.value })} />
          </form>
        )}
      </Modal>
    </Wide>
  )
}
