import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { createRfq } from '../../api/commerce'
import { ApiError } from '../../api/client'

export function RfqPage() {
  const toast = useToast()
  const navigate = useNavigate()
  const [productId, setProductId] = useState('')
  const [qty, setQty] = useState('')
  const [deadline, setDeadline] = useState('')
  const [reqs, setReqs] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      const rfq = await createRfq({
        product_id: Number(productId),
        qty,
        deadline: deadline || undefined,
        qualification_requirements: reqs || undefined,
      })
      toast.success(`تم إنشاء طلب العرض ${rfq.number}.`)
      navigate(`/rfq/${rfq.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الإنشاء')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <PageTitle title="طلب عرض سعر (RFQ)" subtitle="الشركة تتوسّط العروض — هوية الموردين تبقى مخفية عنك." />
      <form onSubmit={submit} className="mt-space-xl flex flex-col gap-space-md max-w-[480px]">
        <Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={productId} onChange={(e) => setProductId(e.target.value)} required />
        <Field label="الكمية المطلوبة" dir="ltr" mono inputMode="decimal" value={qty} onChange={(e) => setQty(e.target.value)} required />
        <Field label="آخر موعد (اختياري)" type="date" dir="ltr" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
        <Field label="متطلبات التأهيل (اختياري)" value={reqs} onChange={(e) => setReqs(e.target.value)} />
        <div className="flex justify-end">
          <Button variant="primary" type="submit" disabled={busy || !productId || !qty}>إرسال الطلب</Button>
        </div>
      </form>
    </Narrow>
  )
}
