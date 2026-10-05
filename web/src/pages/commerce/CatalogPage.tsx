import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, InlineError, Card } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { addCartItem, browseCatalog, type CatalogProduct } from '../../api/commerce'
import { listCategories, PRODUCT_CATEGORIES, type Category } from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

export function CatalogPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('')
  // Seed with the static list so the filter chips/labels never vanish; the
  // backend list (GET /inventory/categories) overrides it once it arrives.
  const [categories, setCategories] = useState<Category[]>(PRODUCT_CATEGORIES)
  const [rows, setRows] = useState<CatalogProduct[]>([])
  const [qty, setQty] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await browseCatalog({ q: q || undefined, category: cat || undefined })
      setRows(r.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [q, cat])

  useEffect(() => { void load() }, [cat]) // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    listCategories()
      .then((r) => { if (r.items.length) setCategories(r.items) })
      .catch(() => { /* keep the static fallback */ })
  }, [])

  const catAr = (code: string) => (code === '' ? 'الكل' : categories.find((c) => c.code === code)?.label ?? code)

  async function add(p: CatalogProduct) {
    setBusyId(p.product_id)
    try {
      await addCartItem(p.best_offer_id, qty[p.product_id] || '1')
      toast.success('أُضيف إلى السلة — السعر مثبّت ٦٠ دقيقة.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّرت الإضافة')
    } finally {
      setBusyId(null)
    }
  }

  const chip = (active: boolean) =>
    `px-3 py-1 rounded-pill font-small text-small transition-colors ${
      active
        ? 'bg-primary text-on-primary shadow-card-sm'
        : 'bg-surface-variant text-on-surface-variant hover:text-primary'
    }`

  return (
    <Wide>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="الكتالوج" subtitle="تصفّح المنتجات بأفضل سعر متاح. السعر يُثبَّت للكمية عند الإضافة للسلة." />
        <Button onClick={() => navigate('/cart')}>السلة</Button>
      </div>

      <div className="mt-space-lg flex flex-col gap-space-md">
        <form onSubmit={(e) => { e.preventDefault(); void load() }} className="max-w-[420px]">
          <Field label="بحث (اسم/كود)" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>
        <div className="flex gap-space-xs flex-wrap">
          {['', ...categories.map((c) => c.code)].map((c) => (
            <button key={c || 'all'} className={chip(cat === c)} onClick={() => setCat(c)}>{catAr(c)}</button>
          ))}
        </div>
      </div>

      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : rows.length === 0 ? (
          <EmptyState title="لا توجد منتجات مطابقة." />
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-space-md">
            {rows.map((p) => (
              <Card
                key={p.product_id}
                className="group flex flex-col gap-space-md transition-all hover:shadow-overlay hover:-translate-y-0.5"
              >
                {/* Image area */}
                <Link
                  to={`/catalog/${p.product_id}`}
                  className="aspect-[4/3] w-full rounded-xl overflow-hidden bg-surface-container-low border border-surface-container-high flex items-center justify-center"
                >
                  {p.image_url ? (
                    <img
                      src={p.image_url}
                      alt={p.name_ar}
                      className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-[1.03]"
                    />
                  ) : (
                    <Icon name="inventory_2" size={36} className="text-outline-variant" />
                  )}
                </Link>

                <div className="flex items-start justify-between gap-space-sm">
                  <Link
                    to={`/catalog/${p.product_id}`}
                    className="font-body-medium text-body-medium text-on-surface hover:text-primary transition-colors line-clamp-2"
                  >
                    {p.name_ar}
                  </Link>
                  <Pill tone="neutral">{catAr(p.category)}</Pill>
                </div>

                <Mono className="text-secondary">{p.sku}</Mono>

                <div className="mt-auto flex items-baseline gap-space-xs" dir="ltr">
                  <span className="font-mono-medium text-headline-1 text-primary">{formatMoney(p.best_price)}</span>
                  <span className="font-small text-small text-secondary">ج.م / {p.unit}</span>
                </div>

                <div className="flex items-center gap-space-sm">
                  <div className="w-20">
                    <Field dir="ltr" mono inputMode="decimal" value={qty[p.product_id] ?? '1'}
                      onChange={(e) => setQty((s) => ({ ...s, [p.product_id]: e.target.value }))} />
                  </div>
                  <Button variant="primary" className="flex-1" onClick={() => add(p)} disabled={busyId === p.product_id} iconRight="add_shopping_cart">
                    {busyId === p.product_id ? '…' : 'أضف للسلة'}
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </Wide>
  )
}
