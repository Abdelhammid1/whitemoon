import { useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, SectionHeader } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { applyEarlyDiscount, createDeferredTerms } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { todayIso } from '../../lib/format'

export function DeferredTermsPage() {
  const toast = useToast()
  const [orderId, setOrderId] = useState('')
  const [cash, setCash] = useState('')
  const [deferred, setDeferred] = useState('')
  const [discount, setDiscount] = useState('0')
  const [before, setBefore] = useState('')
  const [applyOrder, setApplyOrder] = useState('')
  const [settledOn, setSettledOn] = useState(todayIso())
  const [busy, setBusy] = useState(false)

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      const r = await createDeferredTerms({ order_id: Number(orderId), cash_price: cash, deferred_price: deferred, early_settlement_discount: discount, early_settlement_before: before || undefined })
      toast.success(`تم تثبيت شروط الآجل للطلب #${r.order_id}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally {
      setBusy(false)
    }
  }
  async function onApply(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      const r = await applyEarlyDiscount(Number(applyOrder), settledOn)
      toast.success(r.discount_applied ? 'تم تطبيق الخصم.' : 'كان مطبّقًا مسبقًا — لا تغيير.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل التطبيق')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <PageTitle title="البيع الآجل" subtitle="السعر الآجل كامل مُثبت لحظة الطلب — لا فائدة يومية، فقط خصم استحقاق عند السداد المبكر." />

      <section className="mt-space-xl">
        <SectionHeader title="تثبيت شروط الآجل" />
        <form onSubmit={onCreate} className="mt-space-md flex flex-col gap-space-md">
          <Field label="رقم الطلب" dir="ltr" mono inputMode="numeric" value={orderId} onChange={(e) => setOrderId(e.target.value)} required />
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Field label="السعر النقدي (ج.م)" dir="ltr" mono inputMode="decimal" value={cash} onChange={(e) => setCash(e.target.value)} required />
            <Field label="السعر الآجل (ج.م)" dir="ltr" mono inputMode="decimal" value={deferred} onChange={(e) => setDeferred(e.target.value)} required hint="يجب أن يكون ≥ السعر النقدي." />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Field label="خصم السداد المبكر (ج.م)" dir="ltr" mono inputMode="decimal" value={discount} onChange={(e) => setDiscount(e.target.value)} />
            <Field label="آخر تاريخ لاستحقاق الخصم" type="date" dir="ltr" value={before} onChange={(e) => setBefore(e.target.value)} />
          </div>
          <div className="flex justify-end"><Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار الحفظ…' : 'حفظ الشروط'}</Button></div>
        </form>
      </section>

      <section className="mt-[48px]">
        <SectionHeader title="تطبيق خصم السداد المبكر" />
        <form onSubmit={onApply} className="mt-space-md flex flex-wrap items-end gap-space-md">
          <div className="w-40"><Field label="رقم الطلب" dir="ltr" mono inputMode="numeric" value={applyOrder} onChange={(e) => setApplyOrder(e.target.value)} required /></div>
          <div className="w-56"><Field label="تاريخ السداد" type="date" dir="ltr" value={settledOn} onChange={(e) => setSettledOn(e.target.value)} required /></div>
          <Button variant="primary" type="submit" disabled={busy}>تطبيق</Button>
        </form>
      </section>
    </Narrow>
  )
}
