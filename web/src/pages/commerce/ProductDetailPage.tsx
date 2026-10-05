import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, InlineError, SectionHeader } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import {
  addCartItem, getProduct, relatedProducts,
  type CatalogProduct, type ProductDetail,
} from '../../api/commerce'
import { PRODUCT_CATEGORIES } from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

const CAT_LABEL: Record<string, string> = Object.fromEntries(
  PRODUCT_CATEGORIES.map((c) => [c.code, c.label]),
)

export function ProductDetailPage() {
  const { id } = useParams()
  const pid = Number(id)
  const toast = useToast()
  const [product, setProduct] = useState<ProductDetail | null>(null)
  const [related, setRelated] = useState<CatalogProduct[]>([])
  const [qty, setQty] = useState('1')
  const [loading, setLoading] = useState(true)
  const [missing, setMissing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null); setMissing(false)
    try {
      const p = await getProduct(pid)
      setProduct(p)
      const r = await relatedProducts(pid)
      setRelated(r.items)
    } catch (err) {
      if (err instanceof ApiError && err.status === 404) setMissing(true)
      else setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [pid])
  useEffect(() => { void load() }, [load])

  async function add() {
    if (!product) return
    setBusy(true)
    try {
      await addCartItem(product.best_offer_id, qty || '1')
      toast.success('تمت الإضافة للسلة — السعر مثبّت ٦٠ دقيقة.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّرت الإضافة')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (missing)
    return (
      <Narrow>
        <PageTitle title="المنتج" />
        <div className="mt-space-xl"><EmptyState title="المنتج غير متاح." description="قد يكون غير نشط أو لا يوجد عرض سعر متاح حالياً." /></div>
      </Narrow>
    )
  if (error || !product)
    return <Narrow><div className="mt-space-xl"><InlineError message={error ?? 'غير موجود'} /></div></Narrow>

  return (
    <Narrow>
      <div className="flex items-center justify-between gap-space-md">
        <Link to="/catalog" className="font-small text-small text-secondary hover:text-primary">→ الكتالوج</Link>
        <Link to="/cart" className="font-small text-small text-primary hover:underline">السلة</Link>
      </div>

      <div className="mt-space-md flex flex-col md:flex-row gap-space-lg">
        {/* Image */}
        <div className="w-full md:w-[280px] shrink-0">
          {product.image_url ? (
            <img src={product.image_url} alt={product.name_ar} className="w-full h-[220px] object-cover rounded-xl border border-surface-container-high" />
          ) : (
            <div className="w-full h-[220px] rounded-xl border border-surface-container-high bg-surface-container-low flex items-center justify-center text-outline-variant">
              <Icon name="image" size={40} />
            </div>
          )}
        </div>

        {/* Info */}
        <div className="flex flex-col gap-space-sm flex-1 min-w-0">
          <div className="flex items-start justify-between gap-space-sm">
            <h1 className="font-display text-headline-1 text-primary font-medium">{product.name_ar}</h1>
            <Pill tone="neutral">{CAT_LABEL[product.category] ?? product.category}</Pill>
          </div>
          <Mono className="text-secondary">{product.sku}</Mono>
          {(product.brand || product.subcategory) && (
            <div className="flex flex-wrap gap-space-md font-small text-small text-secondary">
              {product.brand && <span>الماركة: <span className="text-on-surface">{product.brand}</span></span>}
              {product.subcategory && <span>التصنيف الفرعي: <span className="text-on-surface">{product.subcategory}</span></span>}
            </div>
          )}
          {product.description && (
            <p className="font-body text-body text-on-surface-variant mt-space-xs">{product.description}</p>
          )}

          <div className="mt-space-sm flex items-baseline gap-space-xs" dir="ltr">
            <span className="font-mono-medium text-display text-primary">{formatMoney(product.best_price)}</span>
            <span className="font-small text-small text-secondary">ج.م / {product.unit}</span>
          </div>

          <div className="mt-space-sm flex items-center gap-space-sm">
            <div className="w-24">
              <Field label="الكمية" dir="ltr" mono inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} />
            </div>
            <Button variant="primary" onClick={() => void add()} disabled={busy}>
              {busy ? '…' : 'أضف للسلة'}
            </Button>
          </div>
          <span className="font-small text-small text-secondary">السعر يُثبَّت ٦٠ دقيقة عند الإضافة.</span>
        </div>
      </div>

      {/* Related */}
      {related.length > 0 && (
        <section className="mt-[48px]">
          <SectionHeader title="منتجات مشابهة" />
          <div className="mt-space-md grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
            {related.map((p) => (
              <Link
                key={p.product_id}
                to={`/catalog/${p.product_id}`}
                className="flex flex-col gap-space-xs rounded-xl bg-surface-container-lowest border border-surface-container-high p-space-md hover:bg-surface transition-colors"
              >
                <span className="font-body-medium text-body-medium text-on-surface">{p.name_ar}</span>
                <Mono className="text-secondary">{p.sku}</Mono>
                <span className="font-display text-headline-2 text-primary"><Mono>{formatMoney(p.best_price)}</Mono> ج.م</span>
              </Link>
            ))}
          </div>
        </section>
      )}
    </Narrow>
  )
}
