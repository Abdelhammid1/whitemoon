import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Pill, Spinner, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { checkout, getCart, removeCartItem, type Cart } from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

export function CartPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [cart, setCart] = useState<Cart | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirm, setConfirm] = useState<null | 'cash' | 'deferred'>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { setCart(await getCart()) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function remove(itemId: number) {
    setBusy(true)
    try { setCart(await removeCartItem(itemId)) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر الحذف') }
    finally { setBusy(false) }
  }

  async function placeOrder(mode: 'cash' | 'deferred') {
    setBusy(true)
    try {
      const order = await checkout(mode)
      toast.success(`تم إنشاء الطلب ${order.number}.`)
      navigate(`/orders/${order.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر إتمام الطلب')
    } finally {
      setBusy(false)
      setConfirm(null)
    }
  }

  return (
    <Narrow>
      <PageTitle title="سلتي" subtitle="سلة موحّدة قد تشمل أكثر من مورد — دون كشف هوية أي مورد." />
      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : !cart || cart.items.length === 0 ? (
          <EmptyState title="سلتك فارغة." description="تصفّح الكتالوج وأضف منتجات." />
        ) : (
          <>
            <DataTable
              rows={cart.items}
              rowKey={(i) => i.item_id}
              columns={[
                { header: 'المنتج', cell: (i) => i.name_ar ?? <Mono>#{i.product_id}</Mono> },
                { header: 'الكمية', align: 'end', cell: (i) => <Mono>{i.qty}</Mono> },
                {
                  header: 'سعر الوحدة',
                  align: 'end',
                  cell: (i) => (
                    <span className="flex items-center justify-end gap-space-xs">
                      <Mono>{formatMoney(i.locked_unit_price)}</Mono>
                      {i.price_locked_until && <Pill tone="signal">مثبّت</Pill>}
                    </span>
                  ),
                },
                { header: 'الإجمالي', align: 'end', cell: (i) => <Mono>{formatMoney(i.line_total)}</Mono> },
                {
                  header: '',
                  align: 'end',
                  cell: (i) => (
                    <button className="text-[#ba1a1a] font-small hover:underline" onClick={() => remove(i.item_id)} disabled={busy}>
                      حذف
                    </button>
                  ),
                },
              ]}
            />
            <div className="mt-space-lg flex items-center justify-between border-t border-surface-container-high pt-space-md">
              <span className="font-body-medium text-body-medium">الإجمالي</span>
              <span className="font-display text-headline-1 text-primary"><Mono>{formatMoney(cart.total)}</Mono> ج.م</span>
            </div>
            <div className="mt-space-lg flex justify-end gap-space-sm">
              <Button onClick={() => setConfirm('deferred')} disabled={busy}>طلب آجل</Button>
              <Button variant="primary" onClick={() => setConfirm('cash')} disabled={busy}>طلب نقدي</Button>
            </div>
          </>
        )}
      </div>

      <Modal
        open={confirm !== null}
        onClose={() => setConfirm(null)}
        title={confirm === 'deferred' ? 'تأكيد الطلب الآجل' : 'تأكيد الطلب النقدي'}
        footer={
          <>
            <Button onClick={() => setConfirm(null)}>إلغاء</Button>
            <Button variant="primary" onClick={() => placeOrder(confirm as 'cash' | 'deferred')} disabled={busy}>تأكيد</Button>
          </>
        }
      >
        <p className="font-body text-body text-secondary">
          {confirm === 'deferred'
            ? 'الشروط المالية للآجل (السعر، الخصم، الموعد) تُحتسب على الخادم تلقائيًا، وقد يُرفض الطلب إذا تجاوز سقفك الائتماني.'
            : 'سيتم إنشاء الطلب فورًا بسعر النقد المثبّت.'}
        </p>
      </Modal>
    </Narrow>
  )
}
