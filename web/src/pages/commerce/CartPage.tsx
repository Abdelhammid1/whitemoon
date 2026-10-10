import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { Button, Spinner, EmptyState, InlineError, Pill, Card } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Icon } from '../../components/Icon'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { checkout, getCart, removeCartItem, updateCartItem, type Cart } from '../../api/commerce'
import { getDeferredQuote, getDeferredOptions, type DeferredQuote, type DeferredOptions } from '../../api/credit'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'
import { PageHelp } from '../../components/PageHelp'

export function CartPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState<null | 'cash' | 'deferred'>(null)
  // Deferred: options (allowed + durations), the chosen duration, and the
  // server-computed quote for it.
  const [deferredDays, setDeferredDays] = useState<number | null>(null)
  const [options, setOptions] = useState<DeferredOptions | null>(null)
  const [quote, setQuote] = useState<DeferredQuote | null>(null)
  const [quoteLoading, setQuoteLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { setCart(await getCart()) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  // When the deferred modal opens, fetch the customer's options (allowed +
  // durations) and pre-select the default duration. Reset on close.
  useEffect(() => {
    if (confirm !== 'deferred') { setOptions(null); setQuote(null); setDeferredDays(null); return }
    let active = true
    getDeferredOptions()
      .then((o) => {
        if (!active) return
        setOptions(o)
        if (o.allowed && o.allowed_days.length) {
          const d = o.allowed_days.includes(o.default_days) ? o.default_days : o.allowed_days[0]
          if (d != null) setDeferredDays(d)
        }
      })
      .catch(() => active && setOptions({ allowed: false, reason: 'تعذّر جلب خيارات الأجل', allowed_days: [], default_days: 0 }))
    return () => { active = false }
  }, [confirm])

  // Recompute the (server-side) quote whenever the chosen duration changes.
  useEffect(() => {
    if (confirm !== 'deferred' || deferredDays == null || !cart) return
    let active = true
    setQuoteLoading(true)
    getDeferredQuote(cart.total, deferredDays)
      .then((q) => { if (active) setQuote(q) })
      .catch(() => { if (active) setQuote(null) })
      .finally(() => { if (active) setQuoteLoading(false) })
    return () => { active = false }
  }, [confirm, deferredDays, cart])

  async function remove(itemId: number) {
    setBusy(true)
    try { setCart(await removeCartItem(itemId)) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر الحذف') }
    finally { setBusy(false) }
  }

  // Qty is a Decimal string on the server; we step by whole units and let the
  // server enforce the offer's MOQ and stock ceiling, surfacing any rejection.
  async function changeQty(itemId: number, current: string, delta: number) {
    const next = Number(current) + delta
    if (!Number.isFinite(next) || next < 1) return
    setBusy(true)
    try { setCart(await updateCartItem(itemId, String(next))) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر تعديل الكمية') }
    finally { setBusy(false) }
  }

  async function placeOrder(mode: 'cash' | 'deferred') {
    setBusy(true)
    try {
      const order = await checkout(mode, mode === 'deferred' ? deferredDays ?? undefined : undefined)
      toast.success(`تم إنشاء الطلب ${order.number}.`)
      navigate(`/orders/${order.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إتمام الطلب')
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  const items = cart?.items ?? []
  const distinctCount = items.length
  const totalUnits = items.reduce((sum, i) => sum + Number(i.qty), 0)

  return (
    <Wide>
      {/* Header context strip */}
      <header className="flex flex-col md:flex-row md:items-baseline justify-between gap-space-sm pb-space-lg mb-space-lg border-b border-surface-container-highest">
        <div>
          <div className="flex items-center gap-space-xs font-mono-body text-mono-body text-secondary mb-1" dir="ltr">
            <span>CART{cart ? ` // #${cart.cart_id}` : ''}</span>
          </div>
          <h1 className="font-display text-display text-primary font-medium tracking-tight">
            السلة الموحدة للمشتريات
          </h1>
          <p className="font-body text-body text-secondary mt-0.5">
            سلة موحّدة قد تشمل أكثر من مورد — هوية الموردين محجوبة بالكامل، والفاتورة باسم وايت مون.
          </p>
        </div>
      </header>

      <PageHelp pageKey="cart" />

      {loading ? (
        <Spinner />
      ) : error ? (
        <InlineError message={error} />
      ) : items.length === 0 ? (
        <EmptyState title="سلتك فارغة." description="تصفّح الكتالوج وأضف منتجات." />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-space-xl items-start">
          {/* Main ledger */}
          <div className="lg:col-span-8 flex flex-col gap-space-lg">
            <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={items}
              rowKey={(i) => i.item_id}
              columns={[
                {
                  header: 'المنتج والتوصيف',
                  cell: (i) => (
                    <span className="font-body-medium text-body-medium text-primary">
                      {i.name_ar ?? <Mono>#{i.product_id}</Mono>}
                    </span>
                  ),
                },
                {
                  header: 'الكمية',
                  align: 'center',
                  width: '8rem',
                  cell: (i) => (
                    <div className="inline-flex items-center gap-1" dir="ltr">
                      <button
                        type="button"
                        className="w-7 h-7 flex items-center justify-center rounded-md border border-surface-container-high text-secondary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed"
                        onClick={() => changeQty(i.item_id, i.qty, -1)}
                        disabled={busy || Number(i.qty) <= 1}
                        title="إنقاص الكمية"
                      >
                        <Icon name="remove" size={16} />
                      </button>
                      <Mono className="text-primary w-10 text-center">{i.qty}</Mono>
                      <button
                        type="button"
                        className="w-7 h-7 flex items-center justify-center rounded-md border border-surface-container-high text-secondary hover:text-primary disabled:opacity-40 disabled:cursor-not-allowed"
                        onClick={() => changeQty(i.item_id, i.qty, 1)}
                        disabled={busy}
                        title="زيادة الكمية"
                      >
                        <Icon name="add" size={16} />
                      </button>
                    </div>
                  ),
                },
                {
                  header: 'سعر الوحدة',
                  align: 'end',
                  cell: (i) => (
                    <div className="flex flex-col items-end gap-0.5">
                      <Mono className="text-primary">{formatMoney(i.locked_unit_price)} ج.م</Mono>
                      {i.price_locked_until ? (
                        <Pill tone="signal">سعر مثبّت</Pill>
                      ) : (
                        <Pill tone="neutral">محدث لحظياً</Pill>
                      )}
                    </div>
                  ),
                },
                {
                  header: 'الإجمالي',
                  align: 'end',
                  cell: (i) => <Mono className="text-primary">{formatMoney(i.line_total)} ج.م</Mono>,
                },
                {
                  header: '',
                  align: 'center',
                  width: '3rem',
                  cell: (i) => (
                    <button
                      type="button"
                      className="text-secondary hover:text-error transition-colors p-1.5 disabled:opacity-40"
                      onClick={() => remove(i.item_id)}
                      disabled={busy}
                      title="حذف الصنف"
                    >
                      <Icon name="delete_outline" size={18} />
                    </button>
                  ),
                },
              ]}
            />
            </Card>

            {/* Neutral-fulfillment / privacy disclosure */}
            <div className="p-space-md rounded-xl bg-surface-container-low flex items-start gap-space-sm">
              <Icon name="verified_user" size={18} className="text-secondary shrink-0 mt-0.5" />
              <div className="flex flex-col font-small text-small text-secondary leading-relaxed">
                <span className="font-small-medium text-small-medium text-primary">
                  ضمان وايت مون للتوريد المحايد
                </span>
                <span>
                  تُجمَّع البنود وتُنفَّذ عبر شبكة موردين معتمدين دون الكشف عن هوية المورد، لحماية
                  استقرار الأسعار والحياد التجاري. الفاتورة والضمان صادران باسم شركة وايت مون.
                </span>
              </div>
            </div>
          </div>

          {/* Order summary panel */}
          <div className="lg:col-span-4 flex flex-col gap-space-md lg:sticky lg:top-space-lg">
            <Card className="flex flex-col">
              <span className="font-mono-body text-mono-body text-secondary mb-space-xs" dir="ltr">
                SUMMARY
              </span>
              <h2 className="font-headline-1 text-headline-1 text-primary font-medium tracking-tight mb-space-md">
                ملخص الطلبية
              </h2>

              <div className="flex flex-col gap-space-sm font-body text-body">
                <div className="flex justify-between items-center text-secondary">
                  <span>عدد الأصناف الفريدة</span>
                  <Mono className="text-primary">{distinctCount}</Mono>
                </div>
                <div className="flex justify-between items-center text-secondary">
                  <span>إجمالي عدد الوحدات</span>
                  <Mono className="text-primary">{totalUnits}</Mono>
                </div>

                <div className="pt-space-md mt-space-xs border-t border-surface-container-high flex justify-between items-baseline">
                  <span className="font-headline-2 text-headline-2 text-primary font-medium">
                    الإجمالي الكلي
                  </span>
                  <span className="font-display text-headline-1 text-primary font-medium tracking-tight">
                    <Mono className="text-primary">{formatMoney(cart!.total)} ج.م</Mono>
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-space-sm mt-space-lg">
                <Button variant="primary" className="w-full py-3" onClick={() => setConfirm('cash')} disabled={busy}>
                  <Icon name="payments" size={18} />
                  <span>إتمام طلب نقدي فوري</span>
                </Button>
                <Button className="w-full py-3" onClick={() => setConfirm('deferred')} disabled={busy}>
                  <Icon name="account_balance_wallet" size={18} />
                  <span>طلب آجل (تسهيلات معتمدة)</span>
                </Button>
              </div>

              <div className="mt-space-md pt-space-sm flex items-center justify-between text-secondary font-small text-small">
                <span>العملة الرسمية المعتمدة:</span>
                <span className="font-mono-medium text-mono-medium text-on-surface" dir="ltr">
                  EGP
                </span>
              </div>
            </Card>

            <div className="p-space-md rounded-xl bg-surface-container-low flex flex-col gap-space-xs font-small text-small text-secondary">
              <div className="flex items-center gap-1.5 text-primary font-body-medium">
                <Icon name="info" size={16} />
                <span>تثبيت السعر</span>
              </div>
              <p>يُثبَّت سعر النقد ٦٠ دقيقة عند الإضافة؛ بعد انقضائها يعود السعر إلى القيمة اللحظية.</p>
            </div>
          </div>
        </div>
      )}

      <Modal
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm === 'deferred' ? 'تأكيد الطلب الآجل' : 'تأكيد الطلب النقدي'}
        footer={
          <>
            <Button onClick={() => setConfirm(null)}>إلغاء</Button>
            <Button
              variant="primary"
              onClick={() => placeOrder(confirm as 'cash' | 'deferred')}
              disabled={busy || (confirm === 'deferred' && (options?.allowed === false || deferredDays == null))}
            >
              تأكيد
            </Button>
          </>
        }
      >
        {confirm === 'deferred' ? (
          <div className="flex flex-col gap-space-md">
            {options?.allowed === false ? (
              <InlineError message={options.reason ?? 'البيع الآجل غير متاح لحسابك حاليًا.'} />
            ) : (
              <>
                <div className="p-space-sm rounded-lg bg-surface-container-low flex items-start gap-space-xs font-small text-small text-secondary">
                  <Icon name="smart_toy" size={16} className="text-on-surface-variant shrink-0 mt-0.5" />
                  <span>
                    رسوم الأجل تُحتسب على الخادم: قيمة الطلب × النسبة السنوية ÷ 365 × عدد الأيام. اختر
                    المدة لترى الرسوم والإجمالي. يخضع الطلب لمراجعة السقف الائتماني عند الإصدار.
                  </span>
                </div>
                <div className="flex flex-col gap-space-xs">
                  <span className="font-small text-small text-secondary">مدة الأجل</span>
                  <div className="flex flex-wrap gap-space-xs">
                    {(options?.allowed_days ?? []).map((d) => (
                      <button
                        key={d}
                        type="button"
                        onClick={() => setDeferredDays(d)}
                        className={`px-3 py-1.5 rounded-lg border font-body text-body transition-colors ${
                          deferredDays === d
                            ? 'border-primary bg-primary/10 text-primary'
                            : 'border-surface-container-high text-secondary hover:text-primary'
                        }`}
                      >
                        {d} يوم
                      </button>
                    ))}
                  </div>
                </div>
                <div className="rounded-xl bg-surface-container p-space-md flex flex-col gap-1">
                  <div className="flex justify-between items-center text-secondary">
                    <span>قيمة الطلب (نقدًا)</span>
                    <Mono className="text-primary">{formatMoney(cart?.total ?? '0')} ج.م</Mono>
                  </div>
                  <div className="flex justify-between items-center text-secondary">
                    <span>رسوم الأجل{quote?.annual_pct ? ` (${quote.annual_pct}% سنويًا × ${quote.days} يوم)` : ''}</span>
                    <Mono className="text-primary">{quoteLoading ? '…' : formatMoney(quote?.fee ?? '0')} ج.م</Mono>
                  </div>
                  <div className="flex justify-between items-baseline pt-space-xs mt-space-xs border-t border-surface-container-high">
                    <span className="font-headline-2 text-headline-2 text-primary">الإجمالي الآجل</span>
                    <span className="font-headline-2 text-headline-2 text-primary">
                      <Mono className="text-primary">{quoteLoading ? '…' : formatMoney(quote?.total ?? cart?.total ?? '0')} ج.م</Mono>
                    </span>
                  </div>
                  {quote?.due_date && (
                    <div className="flex justify-between items-center text-secondary font-small text-small">
                      <span>تاريخ الاستحقاق</span>
                      <span className="font-mono-body text-mono-body text-primary" dir="ltr">{quote.due_date}</span>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        ) : (
          <p className="font-body text-body text-secondary">
            سيتم إنشاء الطلب فورًا بسعر النقد المثبّت.
          </p>
        )}
      </Modal>
    </Wide>
  )
}
