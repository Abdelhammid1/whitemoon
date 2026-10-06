import { useEffect, useMemo, useRef, useState, type FormEvent, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, SectionHeader, Spinner, Card, InlineError } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { useToast } from '../../components/Toast'
import { API_BASE, ApiError } from '../../api/client'
import {
  createProduct, updateProduct, getProductDetail, uploadProductImage,
  deleteProductImage, setPrimaryProductImage, listCategories,
  PRODUCT_CATEGORIES,
  type Category, type ProductStatus, type EtaCodeType,
  type ProductInput, type ProductVariantInput, type ProductImageInput, type InitialBatchInput,
} from '../../api/inventory'

/* ----------------------------------------------------------------- helpers */

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
const MAX_IMAGES = 5

const selectCls =
  'w-full bg-transparent border-b border-surface-container-high py-2 font-body text-body text-on-surface focus:outline-none focus:border-primary focus:border-b-2 transition-all'

let _seq = 0
const nextKey = () => `k${++_seq}`

interface VariantRow extends ProductVariantInput {
  key: string
}
interface ImageItem {
  key: string
  id?: number // present when the image already exists on the server
  url?: string // external url, or the server serve-route url for existing files
  file?: File // a freshly selected file to upload
  preview: string // what to render in <img src>
  isPrimary: boolean
}

/** Resolve the display src for an image item (prefix the api base for the
 *  server serve route; external/object urls are used verbatim). */
function imageSrc(it: ImageItem): string {
  if (it.file) return it.preview
  const url = it.url ?? ''
  return url.startsWith('/inventory/') ? `${API_BASE}${url}` : url
}

const EMPTY_SCALARS = {
  name_ar: '', name_en: '', sku: '', barcode: '', category: '', subcategory: '',
  brand: '', unit: 'piece', description: '',
  status: 'active' as ProductStatus,
  tax_rate: '', eta_code: '', eta_code_type: 'EGS' as EtaCodeType,
  wholesale_price: '', deferred_price: '', default_moq: '',
  food_expiry_tracked: false,
}
const EMPTY_BATCH = { supplier_id: '', batch_code: '', production_date: '', expiry_date: '', qty: '' }

/* ------------------------------------------------------------------- field */

function SelectField({
  label, value, onChange, children,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  children: ReactNode
}) {
  return (
    <div className="w-full flex flex-col">
      <label className="font-small text-small text-secondary mb-1">{label}</label>
      <select className={selectCls} value={value} onChange={(e) => onChange(e.target.value)}>
        {children}
      </select>
    </div>
  )
}

/* -------------------------------------------------------------------- page */

export function ProductFormPage() {
  const { id } = useParams<{ id: string }>()
  const productId = id ? Number(id) : null
  const isEdit = productId != null
  const navigate = useNavigate()
  const toast = useToast()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [categories, setCategories] = useState<Category[]>(PRODUCT_CATEGORIES)
  const [loading, setLoading] = useState(isEdit)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const [form, setForm] = useState({ ...EMPTY_SCALARS })
  const [variants, setVariants] = useState<VariantRow[]>([])
  const [images, setImages] = useState<ImageItem[]>([])
  const [removedImageIds, setRemovedImageIds] = useState<number[]>([])
  const [urlDraft, setUrlDraft] = useState('')
  const [batch, setBatch] = useState({ ...EMPTY_BATCH })

  const set = <K extends keyof typeof form>(k: K, v: (typeof form)[K]) =>
    setForm((f) => ({ ...f, [k]: v }))

  // Load categories; default the category to the first available one on create.
  useEffect(() => {
    listCategories()
      .then((r) => {
        if (r.items.length) {
          setCategories(r.items)
          setForm((f) => (f.category ? f : { ...f, category: r.items[0]!.code }))
        }
      })
      .catch(() => { /* keep static fallback */ })
  }, [])
  useEffect(() => {
    setForm((f) => (f.category ? f : { ...f, category: categories[0]?.code ?? 'food' }))
  }, [categories])

  // Load the product on edit.
  useEffect(() => {
    if (productId == null) return
    let alive = true
    setLoading(true)
    getProductDetail(productId)
      .then((p) => {
        if (!alive) return
        setForm({
          name_ar: p.name_ar ?? '', name_en: p.name_en ?? '', sku: p.sku ?? '',
          barcode: p.barcode ?? '', category: p.category ?? '', subcategory: p.subcategory ?? '',
          brand: p.brand ?? '', unit: p.unit ?? 'piece', description: p.description ?? '',
          status: (p.status ?? 'active') as ProductStatus,
          tax_rate: p.tax_rate ?? '', eta_code: p.eta_code ?? '',
          eta_code_type: (p.eta_code_type ?? 'EGS') as EtaCodeType,
          wholesale_price: p.wholesale_price ?? '', deferred_price: p.deferred_price ?? '',
          default_moq: p.default_moq ?? '',
          food_expiry_tracked: Boolean(p.food_expiry_tracked),
        })
        setVariants((p.variants ?? []).map((v) => ({
          key: nextKey(), sku: v.sku ?? '', barcode: v.barcode ?? '',
          size: v.size ?? '', color: v.color ?? '', pack: v.pack ?? '',
        })))
        setImages((p.images ?? []).map((im) => ({
          key: nextKey(), id: im.id, url: im.url, preview: '', isPrimary: im.is_primary,
        })))
      })
      .catch((e) => toast.error(e instanceof ApiError ? e.message : 'تعذّر تحميل المنتج'))
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [productId]) // eslint-disable-line react-hooks/exhaustive-deps

  // Revoke object URLs for file previews on unmount.
  useEffect(() => () => {
    images.forEach((i) => { if (i.file && i.preview) URL.revokeObjectURL(i.preview) })
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const statusTone = STATUS_TONE[form.status]

  /* ----------------------------------------------------------- variants */
  const addVariant = () =>
    setVariants((v) => [...v, { key: nextKey(), sku: '', barcode: '', size: '', color: '', pack: '' }])
  const removeVariant = (key: string) => setVariants((v) => v.filter((r) => r.key !== key))
  const patchVariant = (key: string, patch: Partial<ProductVariantInput>) =>
    setVariants((v) => v.map((r) => (r.key === key ? { ...r, ...patch } : r)))

  /* ------------------------------------------------------------- images */
  const addImageItems = (items: ImageItem[]) =>
    setImages((cur) => {
      const room = MAX_IMAGES - cur.length
      if (room <= 0) { toast.error(`الحد الأقصى ${MAX_IMAGES} صور`); return cur }
      const add = items.slice(0, room)
      const next = [...cur, ...add]
      // Guarantee exactly one primary.
      if (!next.some((i) => i.isPrimary) && next.length) next[0]!.isPrimary = true
      return next
    })

  const onPickFiles = (files: FileList | null) => {
    if (!files || !files.length) return
    const items: ImageItem[] = Array.from(files).map((file) => ({
      key: nextKey(), file, preview: URL.createObjectURL(file), isPrimary: false,
    }))
    addImageItems(items)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }
  const onAddUrl = () => {
    const url = urlDraft.trim()
    if (!url) return
    addImageItems([{ key: nextKey(), url, preview: url, isPrimary: false }])
    setUrlDraft('')
  }
  const removeImage = (key: string) =>
    setImages((cur) => {
      const target = cur.find((i) => i.key === key)
      if (target?.file && target.preview) URL.revokeObjectURL(target.preview)
      // Already-saved image: remember to delete it on the server at save time.
      if (target?.id != null) setRemovedImageIds((ids) => [...ids, target.id!])
      const next = cur.filter((i) => i.key !== key)
      if (target?.isPrimary && next.length && !next.some((i) => i.isPrimary)) next[0]!.isPrimary = true
      return next
    })
  const setPrimary = (key: string) =>
    setImages((cur) => cur.map((i) => ({ ...i, isPrimary: i.key === key })))

  /* ------------------------------------------------------------- submit */
  function validate(): string | null {
    if (!form.name_ar.trim()) return 'الاسم بالعربية مطلوب'
    if (!form.sku.trim()) return 'SKU مطلوب'
    if (!form.category) return 'الفئة مطلوبة'
    // New products need at least one image; a legacy product being edited may
    // have only image_url and no gallery rows — don't block its save.
    if (!isEdit && images.length < 1) return 'أضف صورة واحدة على الأقل'
    if (images.length > MAX_IMAGES) return `الحد الأقصى ${MAX_IMAGES} صور`
    const dirty = variants.filter((v) => v.sku || v.barcode || v.size || v.color || v.pack)
    if (dirty.some((v) => !v.sku?.trim())) return 'كل متغيّر يحتاج SKU'
    return null
  }

  function buildBody(): ProductInput {
    const trimmedVariants: ProductVariantInput[] = variants
      .filter((v) => v.sku || v.barcode || v.size || v.color || v.pack)
      .map((v) => ({
        sku: (v.sku ?? '').trim(),
        ...(v.barcode?.trim() ? { barcode: v.barcode.trim() } : {}),
        ...(v.size?.trim() ? { size: v.size.trim() } : {}),
        ...(v.color?.trim() ? { color: v.color.trim() } : {}),
        ...(v.pack?.trim() ? { pack: v.pack.trim() } : {}),
      }))
    const body: ProductInput = {
      sku: form.sku.trim(),
      name_ar: form.name_ar.trim(),
      category: form.category,
      unit: form.unit.trim() || 'piece',
      status: form.status,
      food_expiry_tracked: form.food_expiry_tracked,
      eta_code_type: form.eta_code_type,
      ...(form.name_en.trim() ? { name_en: form.name_en.trim() } : {}),
      ...(form.subcategory.trim() ? { subcategory: form.subcategory.trim() } : {}),
      ...(form.brand.trim() ? { brand: form.brand.trim() } : {}),
      ...(form.barcode.trim() ? { barcode: form.barcode.trim() } : {}),
      ...(form.description.trim() ? { description: form.description.trim() } : {}),
      ...(form.tax_rate.trim() ? { tax_rate: form.tax_rate.trim() } : {}),
      ...(form.eta_code.trim() ? { eta_code: form.eta_code.trim() } : {}),
      ...(form.wholesale_price.trim() ? { wholesale_price: form.wholesale_price.trim() } : {}),
      ...(form.deferred_price.trim() ? { deferred_price: form.deferred_price.trim() } : {}),
      ...(form.default_moq.trim() ? { default_moq: form.default_moq.trim() } : {}),
      variants: trimmedVariants,
    }
    return body
  }

  async function onSubmit(e?: FormEvent) {
    e?.preventDefault()
    const v = validate()
    if (v) { setErr(v); toast.error(v); return }
    setErr(null)
    setBusy(true)
    try {
      const body = buildBody()

      if (isEdit && productId != null) {
        // Scalars + variants are lossless to re-send. Images are handled
        // incrementally (the serve route resolves by row id, so a wholesale
        // PUT replace would break uploaded files), so we never send `images`
        // on PUT — only upload the newly added ones.
        await updateProduct(productId, body)
        // Persist existing-image changes: deletions, new uploads, primary pick.
        for (const id of removedImageIds) await deleteProductImage(productId, id)
        const fresh = images.filter((i) => i.id == null)
        for (const i of fresh) {
          const target: File | string | null = i.file ?? i.url ?? null
          if (target) await uploadProductImage(productId, target, i.isPrimary)
        }
        // If the chosen primary is an already-saved image, set it explicitly
        // (a freshly-uploaded primary was handled by its upload call above).
        const primaryExisting = images.find((i) => i.isPrimary && i.id != null)
        if (primaryExisting?.id != null) await setPrimaryProductImage(productId, primaryExisting.id)
        toast.success('تم حفظ التعديلات.')
        navigate('/inventory/products')
        return
      }

      // Create: external-URL images ride in the body; file images upload after.
      const urlImages: ProductImageInput[] = images
        .filter((i) => !i.file && i.url)
        .map((i) => ({ url: i.url!, is_primary: i.isPrimary }))
      const fileImages = images.filter((i) => i.file)
      if (urlImages.length) body.images = urlImages
      if (form.food_expiry_tracked && batch.supplier_id && batch.batch_code) {
        const ib: InitialBatchInput = {
          supplier_id: Number(batch.supplier_id),
          batch_code: batch.batch_code.trim(),
          production_date: batch.production_date,
          expiry_date: batch.expiry_date,
          qty: batch.qty || '0',
        }
        body.initial_batch = ib
      }
      const created = await createProduct(body)
      for (const i of fileImages) {
        if (i.file) await uploadProductImage(created.id, i.file, i.isPrimary)
      }
      toast.success('تم إنشاء المنتج.')
      navigate('/inventory/products')
    } catch (e2) {
      const msg = e2 instanceof ApiError ? e2.message : 'تعذّر الحفظ'
      setErr(msg)
      toast.error(msg)
    } finally {
      setBusy(false)
    }
  }

  const title = isEdit ? 'تعديل المنتج' : 'منتج جديد'
  const foodSuggested = useMemo(() => form.category === 'food', [form.category])

  if (loading) return <Wide><Spinner label="جار تحميل المنتج…" /></Wide>

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle
          title={title}
          subtitle="نموذج احترافي كامل للمنتج — الأساسيات والمتغيّرات والصور والصلاحية والتسعير والضريبة."
        />
        <div className="flex items-center gap-space-sm shrink-0">
          <Button onClick={() => navigate('/inventory/products')}>إلغاء</Button>
          <Button variant="primary" onClick={() => void onSubmit()} disabled={busy} iconRight="check">
            {busy ? 'جارٍ الحفظ…' : 'حفظ'}
          </Button>
        </div>
      </div>

      <form onSubmit={onSubmit} className="mt-space-xl flex flex-col gap-space-lg">
        {/* ------------------------------------------------------ basics */}
        <Card className="flex flex-col gap-space-lg">
          <SectionHeader title="الأساسيات" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="الاسم بالعربية" value={form.name_ar} onChange={(e) => set('name_ar', e.target.value)} required />
            <Field label="الاسم بالإنجليزية (اختياري)" dir="ltr" value={form.name_en} onChange={(e) => set('name_en', e.target.value)} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="SKU" dir="ltr" mono value={form.sku} onChange={(e) => set('sku', e.target.value)} required />
            <Field label="الباركود (اختياري)" dir="ltr" mono value={form.barcode} onChange={(e) => set('barcode', e.target.value)} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <SelectField label="الفئة" value={form.category} onChange={(v) => set('category', v)}>
              {categories.map((c) => <option key={c.code} value={c.code}>{c.label}</option>)}
            </SelectField>
            <Field label="تصنيف فرعي (اختياري)" value={form.subcategory} onChange={(e) => set('subcategory', e.target.value)} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="الماركة (اختياري)" value={form.brand} onChange={(e) => set('brand', e.target.value)} />
            <Field label="الوحدة" value={form.unit} onChange={(e) => set('unit', e.target.value)} hint="مثال: piece، carton، kg" />
          </div>
          <div className="flex flex-col">
            <label className="font-small text-small text-secondary mb-1">الوصف (اختياري)</label>
            <textarea
              className={`${selectCls} resize-y min-h-[88px]`}
              value={form.description}
              onChange={(e) => set('description', e.target.value)}
            />
          </div>
        </Card>

        {/* ---------------------------------------------------- variants */}
        <Card className="flex flex-col gap-space-md">
          <SectionHeader
            title="المتغيّرات"
            action={<Button onClick={addVariant} iconRight="add">إضافة متغيّر</Button>}
          />
          {variants.length === 0 ? (
            <p className="font-body text-body text-secondary py-space-sm">لا توجد متغيّرات — أضف صفًّا لكل مقاس/لون/عبوة.</p>
          ) : (
            <div className="flex flex-col gap-space-sm">
              {variants.map((v) => (
                <div key={v.key} className="grid grid-cols-1 sm:grid-cols-[1fr_1fr_1fr_1.2fr_1.2fr_auto] gap-space-sm items-end rounded-xl bg-surface-container-low p-space-md">
                  <Field label="المقاس" value={v.size ?? ''} onChange={(e) => patchVariant(v.key, { size: e.target.value })} />
                  <Field label="اللون" value={v.color ?? ''} onChange={(e) => patchVariant(v.key, { color: e.target.value })} />
                  <Field label="العبوة" value={v.pack ?? ''} onChange={(e) => patchVariant(v.key, { pack: e.target.value })} />
                  <Field label="SKU" dir="ltr" mono value={v.sku ?? ''} onChange={(e) => patchVariant(v.key, { sku: e.target.value })} />
                  <Field label="الباركود" dir="ltr" mono value={v.barcode ?? ''} onChange={(e) => patchVariant(v.key, { barcode: e.target.value })} />
                  <button
                    type="button"
                    onClick={() => removeVariant(v.key)}
                    aria-label="حذف المتغيّر"
                    className="w-9 h-9 mb-1 rounded-lg flex items-center justify-center text-danger hover:bg-danger-weak transition-colors shrink-0"
                  >
                    <Icon name="delete" size={18} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* ------------------------------------------------------ images */}
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title={`الصور (${images.length}/${MAX_IMAGES})`} />
          <p className="font-small text-small text-secondary">أضف من 1 إلى {MAX_IMAGES} صور، وحدّد صورة رئيسية واحدة. يمكنك رفع ملف أو إضافة رابط.</p>

          {images.length > 0 && (
            <div className="flex flex-wrap gap-space-md">
              {images.map((im) => (
                <div
                  key={im.key}
                  className={`relative w-[120px] rounded-xl overflow-hidden border ${im.isPrimary ? 'border-primary' : 'border-surface-container-high'}`}
                >
                  <div className="h-[120px] bg-surface-container flex items-center justify-center overflow-hidden">
                    {/* eslint-disable-next-line jsx-a11y/alt-text */}
                    <img src={imageSrc(im)} alt="" className="w-full h-full object-cover" />
                  </div>
                  <button
                    type="button"
                    onClick={() => removeImage(im.key)}
                    aria-label="حذف الصورة"
                    className="absolute top-1 start-1 w-7 h-7 rounded-full bg-surface-container-lowest/90 border border-surface-container-high flex items-center justify-center text-danger hover:bg-danger-weak"
                  >
                    <Icon name="close" size={16} />
                  </button>
                  <label className="flex items-center gap-space-xs px-space-sm py-space-xs font-small text-small text-on-surface cursor-pointer">
                    <input
                      type="radio"
                      name="primary-image"
                      checked={im.isPrimary}
                      onChange={() => setPrimary(im.key)}
                    />
                    {im.isPrimary ? 'رئيسية' : 'جعلها رئيسية'}
                  </label>
                </div>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-space-sm sm:flex-row sm:items-end">
            <div className="flex-1 flex items-end gap-space-sm">
              <div className="flex-1">
                <Field
                  label="إضافة عبر رابط"
                  dir="ltr"
                  placeholder="https://…"
                  value={urlDraft}
                  onChange={(e) => setUrlDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); onAddUrl() } }}
                />
              </div>
              <Button onClick={onAddUrl} disabled={!urlDraft.trim() || images.length >= MAX_IMAGES}>إضافة الرابط</Button>
            </div>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp,image/gif"
                multiple
                className="hidden"
                onChange={(e) => onPickFiles(e.target.files)}
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={images.length >= MAX_IMAGES}
                iconRight="upload"
              >
                رفع ملف
              </Button>
            </div>
          </div>
        </Card>

        {/* ----------------------------------------------------- expiry */}
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title="الصلاحية" />
          <label className="flex items-center gap-space-sm font-body text-body text-on-surface cursor-pointer">
            <input
              type="checkbox"
              checked={form.food_expiry_tracked}
              onChange={(e) => set('food_expiry_tracked', e.target.checked)}
            />
            تتبّع صلاحية الأغذية
            {foodSuggested && !form.food_expiry_tracked && (
              <span className="font-small text-small text-secondary">(موصى به للفئة الغذائية)</span>
            )}
          </label>

          {form.food_expiry_tracked && !isEdit && (
            <div className="flex flex-col gap-space-md rounded-xl bg-surface-container-low p-space-md">
              <span className="font-body-medium text-body-medium text-primary">دفعة ابتدائية (اختياري)</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
                <Field label="رقم المورّد (supplier_id)" dir="ltr" mono inputMode="numeric" value={batch.supplier_id} onChange={(e) => setBatch({ ...batch, supplier_id: e.target.value })} />
                <Field label="كود الدفعة" dir="ltr" mono value={batch.batch_code} onChange={(e) => setBatch({ ...batch, batch_code: e.target.value })} />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md">
                <div className="flex flex-col">
                  <label className="font-small text-small text-secondary mb-1">تاريخ الإنتاج</label>
                  <input type="date" dir="ltr" className={selectCls} value={batch.production_date} onChange={(e) => setBatch({ ...batch, production_date: e.target.value })} />
                </div>
                <div className="flex flex-col">
                  <label className="font-small text-small text-secondary mb-1">تاريخ الانتهاء</label>
                  <input type="date" dir="ltr" className={selectCls} value={batch.expiry_date} onChange={(e) => setBatch({ ...batch, expiry_date: e.target.value })} />
                </div>
                <Field label="الكمية" dir="ltr" mono inputMode="decimal" value={batch.qty} onChange={(e) => setBatch({ ...batch, qty: e.target.value })} />
              </div>
            </div>
          )}
          {form.food_expiry_tracked && isEdit && (
            <p className="font-small text-small text-secondary">تُدار الدفعات من شاشة المخزون بعد الإنشاء.</p>
          )}
        </Card>

        {/* ------------------------------------------------------ prices */}
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title="الأسعار" />
          <p className="font-small text-small text-secondary">قيَم مرجعية افتراضية للكتالوج — الأسعار الفعلية تأتي من عروض الموردين.</p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md">
            <Field label="سعر الجملة" dir="ltr" mono inputMode="decimal" hint="ج.م" value={form.wholesale_price} onChange={(e) => set('wholesale_price', e.target.value)} />
            <Field label="السعر الآجل" dir="ltr" mono inputMode="decimal" hint="ج.م" value={form.deferred_price} onChange={(e) => set('deferred_price', e.target.value)} />
            <Field label="الحد الأدنى للطلب" dir="ltr" mono inputMode="decimal" value={form.default_moq} onChange={(e) => set('default_moq', e.target.value)} />
          </div>
        </Card>

        {/* -------------------------------------------------- tax & ETA */}
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title="الضريبة وETA" />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md">
            <Field label="نسبة الضريبة (%)" dir="ltr" mono inputMode="decimal" value={form.tax_rate} onChange={(e) => set('tax_rate', e.target.value)} />
            <Field label="كود ETA" dir="ltr" mono value={form.eta_code} onChange={(e) => set('eta_code', e.target.value)} />
            <SelectField label="نوع كود ETA" value={form.eta_code_type} onChange={(v) => set('eta_code_type', v as EtaCodeType)}>
              <option value="EGS">EGS</option>
              <option value="GS1">GS1</option>
            </SelectField>
          </div>
        </Card>

        {/* ------------------------------------------------------ status */}
        <Card className="flex flex-col gap-space-md">
          <SectionHeader title="الحالة" />
          <div className="flex items-center gap-space-lg">
            <div className="w-[220px]">
              <SelectField label="حالة المنتج" value={form.status} onChange={(v) => set('status', v as ProductStatus)}>
                {(Object.keys(STATUS_LABEL) as ProductStatus[]).map((s) => (
                  <option key={s} value={s}>{STATUS_LABEL[s]}</option>
                ))}
              </SelectField>
            </div>
            <div className="flex items-center gap-space-sm">
              <span className="font-small text-small text-secondary">المعاينة:</span>
              <Pill tone={statusTone}>{STATUS_LABEL[form.status]}</Pill>
            </div>
          </div>
        </Card>

        {err && <InlineError message={err} />}

        <div className="flex items-center justify-end gap-space-sm">
          <Button onClick={() => navigate('/inventory/products')}>إلغاء</Button>
          <Button variant="primary" type="submit" disabled={busy} iconRight="check">
            {busy ? 'جارٍ الحفظ…' : 'حفظ'}
          </Button>
        </div>
      </form>
    </Wide>
  )
}
