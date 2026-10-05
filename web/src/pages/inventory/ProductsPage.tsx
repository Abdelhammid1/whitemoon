import { useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import {
  addVariant, createProduct, listCategories, listProducts, PRODUCT_CATEGORIES,
  type Category, type Product,
} from '../../api/inventory'
import { ApiError } from '../../api/client'

const EMPTY_FORM = {
  sku: '', name_ar: '', name_en: '', category: 'food', subcategory: '', brand: '',
  barcode: '', description: '', image_url: '', unit: 'piece', eta_code: '',
  food_expiry_tracked: false,
}

const EMPTY_VARIANT = { sku: '', barcode: '', size: '', color: '' }

export function ProductsPage() {
  const toast = useToast()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  // Seed with the static list as a fallback so chips/labels never vanish; the
  // backend list (GET /inventory/categories) overrides it once it arrives.
  const [categories, setCategories] = useState<Category[]>(PRODUCT_CATEGORIES)
  const [rows, setRows] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState(EMPTY_FORM)
  const [busy, setBusy] = useState(false)
  // Variant manager
  const [variantFor, setVariantFor] = useState<Product | null>(null)
  const [variant, setVariant] = useState(EMPTY_VARIANT)

  async function load() {
    setLoading(true)
    try {
      const items = (await listProducts({ q: q || undefined, category: category || undefined })).items
      setRows(items)
      // Keep the open variant modal in sync with the refreshed product.
      setVariantFor((cur) => (cur ? items.find((p) => p.id === cur.id) ?? cur : cur))
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [category]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    listCategories()
      .then((r) => { if (r.items.length) setCategories(r.items) })
      .catch(() => { /* keep the static fallback */ })
  }, [])

  const catLabel = (code: string) => categories.find((c) => c.code === code)?.label ?? code

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      // Omit empty optional fields.
      const body = {
        sku: form.sku,
        name_ar: form.name_ar,
        category: form.category,
        food_expiry_tracked: form.food_expiry_tracked,
        ...(form.name_en ? { name_en: form.name_en } : {}),
        ...(form.subcategory ? { subcategory: form.subcategory } : {}),
        ...(form.brand ? { brand: form.brand } : {}),
        ...(form.barcode ? { barcode: form.barcode } : {}),
        ...(form.description ? { description: form.description } : {}),
        ...(form.image_url ? { image_url: form.image_url } : {}),
        ...(form.unit ? { unit: form.unit } : {}),
        ...(form.eta_code ? { eta_code: form.eta_code } : {}),
      }
      await createProduct(body)
      toast.success('تم إنشاء المنتج.')
      setOpen(false)
      setForm(EMPTY_FORM)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الإنشاء')
    } finally {
      setBusy(false)
    }
  }

  async function onAddVariant() {
    if (!variantFor) return
    setBusy(true)
    try {
      await addVariant(variantFor.id, {
        sku: variant.sku,
        ...(variant.barcode ? { barcode: variant.barcode } : {}),
        ...(variant.size ? { size: variant.size } : {}),
        ...(variant.color ? { color: variant.color } : {}),
      })
      toast.success('تم إضافة المتغيّر.')
      setVariant(EMPTY_VARIANT)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل إضافة المتغيّر')
    } finally {
      setBusy(false)
    }
  }

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-mono-body text-small transition-colors ${active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'}`

  const selectCls =
    'bg-transparent border-b border-surface-container-high py-2 font-body text-body focus:outline-none focus:border-primary'

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="المنتجات والمخزون" subtitle="كتالوج موحّد مستقل عن المورد." />
        <Button variant="primary" onClick={() => setOpen(true)} iconRight="add">إضافة منتج</Button>
      </div>

      <div className="mt-space-xl flex flex-wrap items-end gap-space-md">
        <form onSubmit={(e) => { e.preventDefault(); void load() }} className="w-[320px]"><Field label="بحث (SKU / اسم)" value={q} onChange={(e) => setQ(e.target.value)} /></form>
        <div className="flex flex-wrap gap-space-xs">
          <button className={chip(category === '')} onClick={() => setCategory('')}>الكل</button>
          {categories.map((c) => (
            <button key={c.code} className={chip(category === c.code)} onClick={() => setCategory(c.code)}>
              {c.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-space-lg">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(p) => p.id} empty="لا توجد منتجات." columns={[
            { header: 'SKU', cell: (p) => <Mono>{p.sku}</Mono> },
            { header: 'الاسم', cell: (p) => (
              <div className="flex flex-col">
                <span className="font-body text-body">{p.name_ar}</span>
                {p.brand && <span className="font-small text-small text-secondary">{p.brand}</span>}
              </div>
            ) },
            { header: 'الفئة', cell: (p) => <Pill tone="neutral">{catLabel(p.category)}</Pill> },
            { header: 'الوحدة', cell: (p) => <span className="font-body text-body">{p.unit}</span> },
            { header: 'المتغيّرات', align: 'center', cell: (p) => (
              <button className="font-small text-small text-primary hover:underline" onClick={() => { setVariantFor(p); setVariant(EMPTY_VARIANT) }}>
                {(p.variants?.length ?? 0) > 0 ? `${p.variants!.length} متغيّر` : 'إضافة'}
              </button>
            ) },
            { header: 'الحالة', align: 'end', cell: (p) => <Pill tone={p.is_active ? 'signal' : 'neutral'}>{p.is_active ? 'نشط' : 'موقوف'}</Pill> },
          ]} />
        )}
      </div>

      {/* Create product */}
      <Modal open={open} onClose={() => setOpen(false)} title="إضافة منتج جديد" footer={
        <>
          <Button onClick={() => setOpen(false)}>إلغاء</Button>
          <Button variant="primary" onClick={onCreate} disabled={busy || !form.sku || !form.name_ar || !form.category}>حفظ</Button>
        </>
      }>
        <form onSubmit={onCreate} className="flex flex-col gap-space-md">
          <div className="grid grid-cols-2 gap-space-md">
            <Field label="SKU" dir="ltr" mono value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} required />
            <div className="flex flex-col">
              <label className="font-small text-small text-secondary mb-1">الفئة</label>
              <select className={selectCls} value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
                {categories.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
              </select>
            </div>
          </div>
          <Field label="الاسم بالعربية" value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} required />
          <Field label="الاسم بالإنجليزية (اختياري)" dir="ltr" value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
          <div className="grid grid-cols-2 gap-space-md">
            <Field label="تصنيف فرعي (اختياري)" value={form.subcategory} onChange={(e) => setForm({ ...form, subcategory: e.target.value })} />
            <Field label="الماركة (اختياري)" value={form.brand} onChange={(e) => setForm({ ...form, brand: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-space-md">
            <Field label="الباركود (اختياري)" dir="ltr" mono value={form.barcode} onChange={(e) => setForm({ ...form, barcode: e.target.value })} />
            <Field label="الوحدة" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
          </div>
          <Field label="الوصف (اختياري)" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} />
          <Field label="رابط الصورة (اختياري)" dir="ltr" value={form.image_url} onChange={(e) => setForm({ ...form, image_url: e.target.value })} />
          <div className="grid grid-cols-2 gap-space-md items-center">
            <Field label="كود ETA (اختياري)" dir="ltr" mono value={form.eta_code} onChange={(e) => setForm({ ...form, eta_code: e.target.value })} />
            <label className="flex items-center gap-space-sm font-body text-body mt-space-lg">
              <input type="checkbox" checked={form.food_expiry_tracked} onChange={(e) => setForm({ ...form, food_expiry_tracked: e.target.checked })} /> تتبّع الصلاحية
            </label>
          </div>
        </form>
      </Modal>

      {/* Variants manager */}
      <Modal open={variantFor !== null} onClose={() => setVariantFor(null)} title={variantFor ? `متغيّرات: ${variantFor.name_ar}` : 'المتغيّرات'} footer={
        <Button onClick={() => setVariantFor(null)}>إغلاق</Button>
      }>
        {variantFor && (
          <div className="flex flex-col gap-space-md">
            <DataTable rows={variantFor.variants ?? []} rowKey={(v) => v.id} empty="لا توجد متغيّرات بعد." columns={[
              { header: 'SKU', cell: (v) => <Mono>{v.sku}</Mono> },
              { header: 'الباركود', cell: (v) => v.barcode ? <Mono>{v.barcode}</Mono> : <span className="text-secondary">—</span> },
              { header: 'المقاس', cell: (v) => v.size ?? '—' },
              { header: 'اللون', cell: (v) => v.color ?? '—' },
            ]} />
            <div className="border-t border-surface-container-high pt-space-md flex flex-col gap-space-sm">
              <span className="font-body-medium text-body-medium text-primary">إضافة متغيّر</span>
              <div className="grid grid-cols-2 gap-space-md">
                <Field label="SKU" dir="ltr" mono value={variant.sku} onChange={(e) => setVariant({ ...variant, sku: e.target.value })} />
                <Field label="الباركود (اختياري)" dir="ltr" mono value={variant.barcode} onChange={(e) => setVariant({ ...variant, barcode: e.target.value })} />
                <Field label="المقاس (اختياري)" value={variant.size} onChange={(e) => setVariant({ ...variant, size: e.target.value })} />
                <Field label="اللون (اختياري)" value={variant.color} onChange={(e) => setVariant({ ...variant, color: e.target.value })} />
              </div>
              <Button variant="primary" className="self-end" disabled={busy || !variant.sku} onClick={onAddVariant}>إضافة</Button>
            </div>
          </div>
        )}
      </Modal>
    </Wide>
  )
}
