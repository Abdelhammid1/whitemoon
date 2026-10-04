import { useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill } from '../../components/ui'
import { Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { createSale, type PosSale } from '../../api/pos'
import { ApiError } from '../../api/client'
import { formatMoney } from '../../lib/format'

interface Line { product_id: string; supplier_id: string; qty: string }

export function PosPage() {
  const toast = useToast()
  const [lines, setLines] = useState<Line[]>([{ product_id: '', supplier_id: '', qty: '1' }])
  const [busy, setBusy] = useState(false)
  const [last, setLast] = useState<PosSale | null>(null)

  const setLine = (i: number, k: keyof Line, v: string) =>
    setLines((s) => s.map((x, j) => (j === i ? { ...x, [k]: v } : x)))

  async function sell() {
    setBusy(true)
    try {
      const sale = await createSale(
        lines.filter((l) => l.product_id && l.supplier_id).map((l) => ({
          product_id: Number(l.product_id), supplier_id: Number(l.supplier_id), qty: Number(l.qty || '1'),
        })),
      )
      setLast(sale)
      setLines([{ product_id: '', supplier_id: '', qty: '1' }])
      toast.success(`تم البيع ${sale.number}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل البيع')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Wide>
      <PageTitle title="نقطة البيع" subtitle="بيع مباشر من مخزونك — السعر من عرض المورد الفعّال، والقيد المحاسبي يُرحَّل دفعيًا." />

      <div className="mt-space-xl flex flex-col gap-space-sm max-w-[640px]">
        {lines.map((l, i) => (
          <div key={i} className="flex gap-space-sm items-end">
            <Field label={i === 0 ? 'المنتج' : undefined} dir="ltr" mono placeholder="product id" value={l.product_id} onChange={(e) => setLine(i, 'product_id', e.target.value)} />
            <Field label={i === 0 ? 'المورد' : undefined} dir="ltr" mono placeholder="supplier id" value={l.supplier_id} onChange={(e) => setLine(i, 'supplier_id', e.target.value)} />
            <Field label={i === 0 ? 'الكمية' : undefined} dir="ltr" mono placeholder="qty" value={l.qty} onChange={(e) => setLine(i, 'qty', e.target.value)} />
          </div>
        ))}
        <button className="font-small text-primary hover:underline self-start" onClick={() => setLines((s) => [...s, { product_id: '', supplier_id: '', qty: '1' }])}>+ صنف</button>
        <div className="flex justify-end mt-space-md">
          <Button variant="primary" onClick={sell} disabled={busy || !lines.some((l) => l.product_id)}>إتمام البيع (نقدي)</Button>
        </div>
      </div>

      {last && (
        <div className="mt-space-xl border-t border-surface-container-high pt-space-lg max-w-[640px]">
          <div className="flex items-center justify-between">
            <span className="font-body-medium">{last.number}</span>
            <Pill tone={last.posted ? 'signal' : 'warning'}>{last.posted ? 'مُرحَّل' : 'غير مُرحَّل'}</Pill>
          </div>
          <div className="mt-space-sm flex items-center justify-between">
            <span className="font-small text-small text-secondary">الإجمالي</span>
            <span className="font-display text-headline-1 text-primary"><Mono>{formatMoney(last.total)}</Mono> ج.م</span>
          </div>
        </div>
      )}
    </Wide>
  )
}
