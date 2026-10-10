import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  supplierProducts, setSupplierProduct, createCodingRequest,
  downloadProductsTemplate, exportMyProducts, bulkPreviewProducts, bulkApplyProducts,
  type SupplierProduct, type BulkPreview,
} from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

const BULK_TONE: Record<string, 'signal' | 'warning' | 'error'> = { green: 'signal', yellow: 'warning', red: 'error' }
const BULK_AR: Record<string, string> = { green: 'جاهز', yellow: 'تنبيه', red: 'خطأ' }

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
  // T-39 bulk Excel update.
  const bulkRef = useRef<HTMLInputElement>(null)
  const [bulkFile, setBulkFile] = useState<File | null>(null)
  const [bulkPreview, setBulkPreview] = useState<BulkPreview | null>(null)
  const [bulkBusy, setBulkBusy] = useState(false)

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

  async function onBulkFile(file: File | null) {
    if (!file) return
    setBulkFile(file)
    setBulkBusy(true)
    try {
      setBulkPreview(await bulkPreviewProducts(file))
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّرت قراءة الملف')
    } finally {
      setBulkBusy(false)
      if (bulkRef.current) bulkRef.current.value = ''
    }
  }
  async function applyBulk() {
    if (!bulkFile) return
    setBulkBusy(true)
    try {
      const r = await bulkApplyProducts(bulkFile)
      toast.success(`حُفظ ${r.applied} من ${r.total} صف.`)
      setBulkPreview(null); setBulkFile(null)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الحفظ')
    } finally { setBulkBusy(false) }
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
        <div className="flex flex-wrap gap-space-sm">
          <Button onClick={() => void downloadProductsTemplate()} iconRight="download">قالب Excel</Button>
          <Button onClick={() => void exportMyProducts()} iconRight="file_download">تصدير الحالي</Button>
          <Button onClick={() => bulkRef.current?.click()} disabled={bulkBusy} iconRight="upload_file">{bulkBusy && !bulkPreview ? 'جارٍ القراءة…' : 'رفع من ملف'}</Button>
          <Button onClick={() => setCoding({ name: '', barcode: '', brand: '', category: '', note: '' })} iconRight="note_add">اطلب تكويد صنف</Button>
          <Button variant="primary" onClick={openAdd} iconRight="add">إضافة منتج</Button>
        </div>
      </div>
      <input ref={bulkRef} type="file" accept=".xlsx" className="hidden" onChange={(e) => void onBulkFile(e.target.files?.[0] ?? null)} />

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

      {/* T-39: bulk-update preview — colour-coded rows before saving. */}
      <Modal open={bulkPreview !== null} onClose={() => { setBulkPreview(null); setBulkFile(null) }} title="معاينة التحديث بالملف" footer={
        <>
          <Button onClick={() => { setBulkPreview(null); setBulkFile(null) }}>إلغاء</Button>
          <Button variant="primary" disabled={bulkBusy || !bulkPreview || bulkPreview.counts.green + bulkPreview.counts.yellow === 0} onClick={() => void applyBulk()}>
            {bulkBusy ? 'جارٍ الحفظ…' : 'حفظ الصفوف الصالحة'}
          </Button>
        </>
      }>
        {bulkPreview && (
          <div className="flex flex-col gap-space-md">
            <div className="flex flex-wrap gap-space-sm">
              <Pill tone="signal">جاهز {bulkPreview.counts.green}</Pill>
              <Pill tone="warning">تنبيه {bulkPreview.counts.yellow}</Pill>
              <Pill tone="error">خطأ {bulkPreview.counts.red}</Pill>
            </div>
            <p className="font-small text-small text-secondary">تُحفظ الصفوف «جاهز» و«تنبيه» فقط؛ الصفوف ذات الخطأ تُتجاهل. السبب مبيّن بكل صف.</p>
            <div className="max-h-[50vh] overflow-auto">
              <DataTable rows={bulkPreview.rows.map((r, i) => ({ ...r, _i: i }))} rowKey={(r) => r._i} columns={[
                { header: 'الباركود', cell: (r) => <Mono>{r.barcode || '—'}</Mono> },
                { header: 'الصنف', cell: (r) => <span className="text-on-surface">{r.name || '—'}</span> },
                { header: 'الحالة', align: 'center', cell: (r) => <Pill tone={BULK_TONE[r.status] ?? 'neutral'}>{BULK_AR[r.status] ?? r.status}</Pill> },
                { header: 'الملاحظة', cell: (r) => <span className="font-small text-small text-secondary">{r.message}</span> },
              ]} />
            </div>
          </div>
        )}
      </Modal>
    </Wide>
  )
}
