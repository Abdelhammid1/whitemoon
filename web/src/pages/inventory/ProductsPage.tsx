import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { Icon } from '../../components/Icon'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  addVariant, bestPrice, listCategories, listProducts, PRODUCT_CATEGORIES,
  type Category, type Product, type ProductStatus,
} from '../../api/inventory'
import { ApiError, API_BASE } from '../../api/client'

const EMPTY_VARIANT = { sku: '', barcode: '', size: '', color: '', pack: '' }

const STATUS_LABEL: Record<ProductStatus, string> = {
  active: 'نشط',
  draft: 'مسودة',
  suspended: 'موقوف',
}
const STATUS_TONE: Record<ProductStatus, 'signal' | 'warning' | 'error'> = {
  active: 'signal',
  draft: 'warning',
  suspended: 'error',
}

/** Resolve a product thumbnail src (prefix the api base for the serve route). */
function thumbSrc(url: string): string {
  return url.startsWith('/inventory/') ? `${API_BASE}${url}` : url
}

export function ProductsPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  // Seed with the static list as a fallback so chips/labels never vanish; the
  // backend list (GET /inventory/categories) overrides it once it arrives.
  const [categories, setCategories] = useState<Category[]>(PRODUCT_CATEGORIES)
  const [rows, setRows] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  // Variant manager
  const [variantFor, setVariantFor] = useState<Product | null>(null)
  const [variant, setVariant] = useState(EMPTY_VARIANT)
  // Best-price lookup (per-row); tracks which product is being queried.
  const [priceBusy, setPriceBusy] = useState<number | null>(null)

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

  async function onBestPrice(p: Product) {
    setPriceBusy(p.id)
    try {
      const r = await bestPrice(p.id)
      if (r.best) {
        toast.info(`أفضل سعر لـ ${p.name_ar}: ${r.best.best_price} ج.م (حد أدنى ${r.best.moq})`)
      } else {
        toast.info(`${p.name_ar}: لا يوجد عرض`)
      }
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر جلب أفضل سعر')
    } finally {
      setPriceBusy(null)
    }
  }

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-small text-small transition-colors ${active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'}`

  const statusOf = (p: Product): ProductStatus =>
    p.status ?? (p.is_active ? 'active' : 'suspended')

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="المنتجات والمخزون" subtitle="كتالوج موحّد مستقل عن المورد." />
        <Button variant="primary" onClick={() => navigate('/inventory/products/new')} iconRight="add">منتج جديد</Button>
      </div>

      <PageHelp pageKey="products" />

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

      <Card padded={false} className="mt-space-lg overflow-hidden">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(p) => p.id} empty="لا توجد منتجات." columns={[
            { header: 'الصورة', cell: (p) => (
              <div className="w-10 h-10 rounded-lg bg-surface-container flex items-center justify-center overflow-hidden shrink-0">
                {p.image_url
                  ? <img src={thumbSrc(p.image_url)} alt="" className="w-full h-full object-cover" />
                  : <Icon name="image" size={18} className="text-outline" />}
              </div>
            ) },
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
            { header: 'أفضل سعر', align: 'center', cell: (p) => (
              <button className="font-small text-small text-primary hover:underline disabled:opacity-40" disabled={priceBusy === p.id} onClick={() => void onBestPrice(p)}>
                {priceBusy === p.id ? '...' : 'أفضل سعر'}
              </button>
            ) },
            { header: 'الحالة', cell: (p) => <Pill tone={STATUS_TONE[statusOf(p)]}>{STATUS_LABEL[statusOf(p)]}</Pill> },
            { header: '', align: 'end', cell: (p) => (
              <button className="font-small-medium text-small-medium text-primary px-space-sm py-1 rounded-lg hover:bg-surface-container-low" onClick={() => navigate(`/inventory/products/${p.id}/edit`)}>
                تعديل
              </button>
            ) },
          ]} />
        )}
      </Card>

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
              { header: 'العبوة', cell: (v) => v.pack ?? '—' },
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
