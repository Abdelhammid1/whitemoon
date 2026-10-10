import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, InlineError, Card } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import {
  addCartItem, browseCatalog, getUsualCategories, getUsualItems,
  type CatalogProduct, type UsualCategory, type UsualItem,
} from '../../api/commerce'
import { listCategories, PRODUCT_CATEGORIES, type Category } from '../../api/inventory'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'
import { PageHelp } from '../../components/PageHelp'

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
  const [usualCats, setUsualCats] = useState<UsualCategory[]>([])
  const [usualItems, setUsualItems] = useState<UsualItem[]>([])

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
    getUsualCategories().then((r) => setUsualCats(r.items)).catch(() => { /* optional */ })
    getUsualItems().then((r) => setUsualItems(r.items)).catch(() => { /* optional */ })
  }, [])

  const catAr = (code: string) => (code === '' ? 'الكل' : categories.find((c) => c.code === code)?.label ?? code)
  // Main/sub grouping (T-32); degrades to a flat list when no parent data.
  const mains = categories.filter((c) => !c.parent_code)
  const subsOf = (code: string) => categories.filter((c) => c.parent_code === code)
  // The main whose subtree the current selection belongs to (to reveal its subs).
  const activeMain = cat && subsOf(cat).length === 0
    ? (categories.find((c) => c.code === cat)?.parent_code ?? cat)
    : cat

  async function addUsual(it: UsualItem) {
    setBusyId(it.product_id)
    try {
      await addCartItem(it.best_offer_id, it.usual_qty || '1')
      toast.success('أُضيف إلى السلة بالكمية المعتادة.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّرت الإضافة')
    } finally { setBusyId(null) }
  }

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
      <PageHelp pageKey="catalog" />

      {/* T-42: «أصنافي المعتادة» — one-click re-add at the current price. */}
      {usualItems.length > 0 && (
        <section className="mt-space-lg">
          <span className="font-body-medium text-body-medium text-primary">أصنافي المعتادة</span>
          <div className="mt-space-sm flex gap-space-sm overflow-x-auto pb-space-xs">
            {usualItems.map((it) => (
              <div key={it.product_id} className="shrink-0 w-44 rounded-xl border border-surface-container-high p-space-sm flex flex-col gap-space-xs">
                <span className="font-small text-small text-on-surface line-clamp-1">{it.name_ar}</span>
                <span className="font-mono-body text-small text-secondary" dir="ltr">{formatMoney(it.best_price)} ج.م</span>
                <Button variant="primary" disabled={busyId === it.product_id} onClick={() => void addUsual(it)} iconRight="add_shopping_cart">
                  {busyId === it.product_id ? '…' : `أضف ${Number(it.usual_qty)}`}
                </Button>
              </div>
            ))}
          </div>
        </section>
      )}

      <div className="mt-space-lg flex flex-col gap-space-md">
        <form onSubmit={(e) => { e.preventDefault(); void load() }} className="max-w-[420px]">
          <Field label="بحث (اسم/كود)" value={q} onChange={(e) => setQ(e.target.value)} />
        </form>

        {/* T-32: «فئاتك المعتادة» first (last-90-day habits, else trending). */}
        {usualCats.length > 0 && (
          <div className="flex flex-col gap-space-xs">
            <span className="font-small text-small text-secondary">{usualCats[0]?.fallback ? 'الأكثر طلبًا' : 'فئاتك المعتادة'}</span>
            <div className="flex gap-space-xs flex-wrap">
              {usualCats.map((uc) => (
                <button key={uc.category} className={chip(cat === uc.category)} onClick={() => setCat(uc.category)}>
                  {catAr(uc.category)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Main categories, then the active main's subcategories (if any). */}
        <div className="flex gap-space-xs flex-wrap">
          <button className={chip(cat === '')} onClick={() => setCat('')}>الكل</button>
          {mains.map((c) => (
            <button key={c.code} className={chip(cat === c.code || activeMain === c.code)} onClick={() => setCat(c.code)}>{c.label}</button>
          ))}
        </div>
        {activeMain && subsOf(activeMain).length > 0 && (
          <div className="flex gap-space-xs flex-wrap ps-space-md border-r-2 border-surface-container-high">
            {subsOf(activeMain).map((s) => (
              <button key={s.code} className={chip(cat === s.code)} onClick={() => setCat(s.code)}>{s.label}</button>
            ))}
          </div>
        )}
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
