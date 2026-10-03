import { useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { applyEarlyDiscount, createDeferredTerms } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'
import { todayIso } from '../../lib/format'

export function DeferredTermsPage() {
  const toast = useToast()

  const [orderId, setOrderId] = useState<string>('')
  const [cashPrice, setCashPrice] = useState<string>('')
  const [deferredPrice, setDeferredPrice] = useState<string>('')
  const [discount, setDiscount] = useState<string>('0')
  const [before, setBefore] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)

  const [applyOrderId, setApplyOrderId] = useState<string>('')
  const [settledOn, setSettledOn] = useState<string>(todayIso())

  async function onCreate(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true)
    try {
      const resp = await createDeferredTerms({
        order_id: Number(orderId),
        cash_price: cashPrice,
        deferred_price: deferredPrice,
        early_settlement_discount: discount,
        early_settlement_before: before || undefined,
      })
      toast.success(`تم تثبيت شروط الآجل للطلب #${resp.order_id}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally {
      setBusy(false)
    }
  }

  async function onApply(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true)
    try {
      const resp = await applyEarlyDiscount(Number(applyOrderId), settledOn)
      toast.success(
        resp.discount_applied ? 'تم تطبيق الخصم.' : 'كان مطبّقًا مسبقًا — لا تغيير.',
      )
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل التطبيق')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="شروط البيع الآجل (شرعي — US-3.4)"
          subtitle="السعر الآجل كامل مُثبت لحظة الطلب، لا توجد فائدة يومية. فقط خصم استحقاق عند السداد المبكر."
        />
        <form onSubmit={onCreate} className="flex flex-col gap-3">
          <Input
            label="رقم الطلب"
            dir="ltr"
            inputMode="numeric"
            value={orderId}
            onChange={(e) => setOrderId(e.target.value)}
            required
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="السعر النقدي (ج.م)"
              dir="ltr"
              inputMode="decimal"
              value={cashPrice}
              onChange={(e) => setCashPrice(e.target.value)}
              required
            />
            <Input
              label="السعر الآجل (ج.م)"
              dir="ltr"
              inputMode="decimal"
              value={deferredPrice}
              onChange={(e) => setDeferredPrice(e.target.value)}
              required
              hint="يجب أن يكون ≥ السعر النقدي."
            />
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="خصم السداد المبكر (ج.م)"
              dir="ltr"
              inputMode="decimal"
              value={discount}
              onChange={(e) => setDiscount(e.target.value)}
            />
            <Input
              label="المهلة لاستحقاق الخصم (قبل تاريخ)"
              type="date"
              dir="ltr"
              value={before}
              onChange={(e) => setBefore(e.target.value)}
            />
          </div>
          <div className="flex justify-end">
            <Button variant="filled" type="submit" disabled={busy}>
              {busy ? 'جار الحفظ…' : 'حفظ الشروط'}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeader
          title="تطبيق خصم السداد المبكر"
          subtitle="فعّال فقط إذا سُدِّد قبل التاريخ المحدد."
        />
        <form onSubmit={onApply} className="flex flex-wrap items-end gap-3">
          <div className="w-40">
            <Input
              label="رقم الطلب"
              dir="ltr"
              inputMode="numeric"
              value={applyOrderId}
              onChange={(e) => setApplyOrderId(e.target.value)}
              required
            />
          </div>
          <div className="w-56">
            <Input
              label="تاريخ السداد"
              type="date"
              dir="ltr"
              value={settledOn}
              onChange={(e) => setSettledOn(e.target.value)}
              required
            />
          </div>
          <Button variant="filled" type="submit" disabled={busy}>
            تطبيق
          </Button>
        </form>
      </Card>
    </div>
  )
}
