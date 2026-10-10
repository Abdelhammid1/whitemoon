import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { Button, Spinner, EmptyState, InlineError, Pill } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Icon } from '../../components/Icon'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  quickSearch, catalogFilterOptions, addCartItem,
  type QuickSearchItem, type FilterOptions, type QuickSearchParams,
} from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

type Sort = NonNullable<QuickSearchParams['sort']>

const selectCls =
  'bg-transparent border-b border-surface-container-high py-1.5 font-body text-body text-on-surface focus:outline-none focus:border-primary'

function defaultQty(it: QuickSearchItem): string {
  const m = Number(it.moq)
  return m > 0 ? String(m) : '1'
}

export function QuickOrderPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const searchRef = useRef<HTMLInputElement>(null)

  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [brand, setBrand] = useState('')
  const [priceMin, setPriceMin] = useState('')
  const [priceMax, setPriceMax] = useState('')
  const [inStock, setInStock] = useState(false)
  const [sort, setSort] = useState<Sort>('relevance')

  const [options, setOptions] = useState<FilterOptions>({ brands: [], categories: [] })
  const [rows, setRows] = useState<QuickSearchItem[]>([])
  const [qty, setQty] = useState<Record<number, string>>({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)
  const [flash, setFlash] = useState<Record<number, boolean>>({})
  const [added, setAdded] = useState(0)

  useEffect(() => {
    catalogFilterOptions().then(setOptions).catch(() => { /* filters optional */ })
    searchRef.current?.focus()
  }, [])

  const search = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await quickSearch({
        q: q || undefined,
        category: category || undefined,
        brand: brand || undefined,
        price_min: priceMin || undefined,
        price_max: priceMax || undefined,
        in_stock: inStock ? '1' : undefined,
        sort,
      })
      setRows(r.items)
      // Seed a default qty for any new rows without clobbering typed values.
      setQty((prev) => {
        const next = { ...prev }
        for (const it of r.items) if (next[it.product_id] === undefined) next[it.product_id] = defaultQty(it)
        return next
      })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر البحث')
    } finally {
      setLoading(false)
    }
  }, [q, category, brand, priceMin, priceMax, inStock, sort])

  // Debounced re-search on any query/filter change.
  useEffect(() => {
    const t = setTimeout(() => { void search() }, 250)
    return () => clearTimeout(t)
  }, [search])

  async function add(it: QuickSearchItem) {
    const quantity = (qty[it.product_id] ?? defaultQty(it)).trim() || defaultQty(it)
    setBusyId(it.product_id)
    try {
      await addCartItem(it.best_offer_id, quantity)
      setAdded((n) => n + 1)
      setFlash((f) => ({ ...f, [it.product_id]: true }))
      setTimeout(() => setFlash((f) => ({ ...f, [it.product_id]: false })), 1500)
      // Ready for the next item: clear the search and refocus it.
      setQ('')
      searchRef.current?.focus()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّرت الإضافة')
    } finally {
      setBusyId(null)
    }
  }

  function onSearchKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && rows.length > 0) {
      e.preventDefault()
      document.getElementById(`qo-qty-${rows[0]!.product_id}`)?.focus()
    }
  }

  return (
    <Wide>
      <header className="flex flex-wrap items-start justify-between gap-space-sm">
        <div className="flex flex-col">
          <div className="font-mono-body text-mono-body text-secondary mb-1" dir="ltr">QUICK // ORDER</div>
          <h1 className="font-display text-display text-primary font-medium tracking-tight">طلب سريع</h1>
          <p className="font-body text-body text-secondary mt-0.5">
            للمشتري بالجملة: ابحث، اكتب الكمية، واضغط Enter للإضافة — كرّر حتى تنتهي.
          </p>
        </div>
        <div className="flex items-center gap-space-sm">
          <span className="font-small text-small text-secondary">أُضيف <Mono>{added}</Mono> صنفًا</span>
          <Button variant="primary" onClick={() => navigate('/cart')} iconRight="shopping_cart">الذهاب للسلة</Button>
        </div>
      </header>

      <PageHelp pageKey="quick-order" />

      {/* Search + filters */}
      <div className="mt-space-lg flex flex-col gap-space-md">
        <div className="relative">
          <Icon name="search" size={18} className="absolute start-3 top-1/2 -translate-y-1/2 text-secondary" />
          <input
            ref={searchRef}
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={onSearchKeyDown}
            placeholder="ابحث بالاسم أو الباركود أو الكود…"
            className="w-full bg-surface-container-lowest border border-surface-container-high rounded-xl ps-10 pe-4 py-3 font-body text-body text-on-surface focus:outline-none focus:border-primary placeholder:text-outline-variant"
          />
        </div>

        <div className="flex flex-wrap items-end gap-space-md">
          <label className="flex flex-col gap-1">
            <span className="font-small text-small text-secondary">الفئة</span>
            <select className={selectCls} value={category} onChange={(e) => setCategory(e.target.value)}>
              <option value="">كل الفئات</option>
              {options.categories.map((c) => <option key={c.code} value={c.code}>{c.name_ar}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-small text-small text-secondary">الماركة</span>
            <select className={selectCls} value={brand} onChange={(e) => setBrand(e.target.value)}>
              <option value="">كل الماركات</option>
              {options.brands.map((b) => <option key={b} value={b}>{b}</option>)}
            </select>
          </label>
          <label className="flex flex-col gap-1 w-24">
            <span className="font-small text-small text-secondary">من سعر</span>
            <input dir="ltr" inputMode="decimal" value={priceMin} onChange={(e) => setPriceMin(e.target.value)} className={selectCls + ' text-center font-mono-body'} />
          </label>
          <label className="flex flex-col gap-1 w-24">
            <span className="font-small text-small text-secondary">إلى سعر</span>
            <input dir="ltr" inputMode="decimal" value={priceMax} onChange={(e) => setPriceMax(e.target.value)} className={selectCls + ' text-center font-mono-body'} />
          </label>
          <label className="flex flex-col gap-1">
            <span className="font-small text-small text-secondary">الترتيب</span>
            <select className={selectCls} value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
              <option value="relevance">الأفضل مطابقة</option>
              <option value="price_asc">الأرخص</option>
              <option value="price_desc">الأغلى</option>
              <option value="name">الاسم</option>
            </select>
          </label>
          <label className="flex items-center gap-space-xs font-body text-body text-secondary self-center pt-4">
            <input type="checkbox" checked={inStock} onChange={(e) => setInStock(e.target.checked)} />
            المتاح فقط
          </label>
        </div>
      </div>

      <div className="mt-space-lg">
        {loading && rows.length === 0 ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : rows.length === 0 ? (
          <EmptyState title="لا توجد نتائج." description="جرّب اسمًا أو كودًا آخر، أو خفّف عوامل التصفية." />
        ) : (
          <DataTable
            rows={rows}
            rowKey={(it) => it.product_id}
            columns={[
              {
                header: 'المنتج',
                cell: (it) => (
                  <span className="flex flex-col">
                    <span className="font-body-medium text-body-medium text-primary">{it.name_ar}</span>
                    <span className="font-mono-body text-small text-secondary" dir="ltr">
                      {it.barcode || it.sku}{it.brand ? ` · ${it.brand}` : ''}
                    </span>
                  </span>
                ),
              },
              { header: 'السعر', align: 'end', cell: (it) => <Mono>{formatMoney(it.best_price)} / {it.unit}</Mono> },
              {
                header: 'المتاح', align: 'end',
                cell: (it) => it.in_stock
                  ? <Pill tone="signal">متاح</Pill>
                  : <span className="font-small text-small text-secondary">نفد</span>,
              },
              {
                header: 'الكمية', align: 'center', width: '7rem',
                cell: (it) => (
                  <input
                    id={`qo-qty-${it.product_id}`}
                    dir="ltr"
                    inputMode="decimal"
                    value={qty[it.product_id] ?? defaultQty(it)}
                    onChange={(e) => setQty((s) => ({ ...s, [it.product_id]: e.target.value }))}
                    onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); void add(it) } }}
                    className="w-20 bg-transparent border-b border-surface-container-high py-1 text-center font-mono-body text-mono-body text-on-surface focus:outline-none focus:border-primary"
                  />
                ),
              },
              {
                header: 'الإجمالي', align: 'end',
                cell: (it) => <Mono className="text-secondary">{formatMoney(Number(it.best_price) * (Number(qty[it.product_id] ?? defaultQty(it)) || 0))}</Mono>,
              },
              {
                header: '', align: 'end', width: '7rem',
                cell: (it) => flash[it.product_id] ? (
                  <span className="inline-flex items-center gap-1 font-small-medium text-small text-signal">
                    <Icon name="check_circle" size={16} /> أُضيف
                  </span>
                ) : (
                  <Button variant="primary" disabled={busyId === it.product_id} onClick={() => void add(it)} iconRight="add_shopping_cart">
                    {busyId === it.product_id ? '…' : 'أضف'}
                  </Button>
                ),
              },
            ]}
          />
        )}
      </div>
    </Wide>
  )
}
