import { useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Field, Spinner, Button } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { adjustStock, reorderCheck, stockBalances, type StockBalance } from '../../api/inventory'
import { ApiError } from '../../api/client'

const LOC_AR: Record<string, string> = {
  supplier: 'مخزن المورد', channel_partner: 'عهدة وكيل/فرع', in_transit: 'في الطريق', customer_hold: 'حجز عميل',
}

const LOC_TYPES = ['supplier', 'channel_partner', 'in_transit', 'customer_hold']

const EMPTY_ADJUST = {
  supplier_id: '', product_id: '', location_type: 'supplier', location_id: '', delta: '', reorder_point: '',
}

export function StockPage() {
  const toast = useToast()
  const { user } = useAuth()
  const isAdmin = user?.kind === 'admin' || user?.kind === 'staff'
  const [supplierId, setSupplierId] = useState('')
  const [location, setLocation] = useState('')
  const [rows, setRows] = useState<StockBalance[]>([])
  const [loading, setLoading] = useState(true)
  const [adjustOpen, setAdjustOpen] = useState(false)
  const [adjust, setAdjust] = useState(EMPTY_ADJUST)
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const resp = await stockBalances({
        supplier_id: isAdmin && supplierId ? Number(supplierId) : undefined,
        location_type: location || undefined,
      })
      setRows(resp.items)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { void load() }, [location]) // eslint-disable-line react-hooks/exhaustive-deps

  async function onReorder() {
    try {
      const r = await reorderCheck(isAdmin && supplierId ? Number(supplierId) : undefined)
      toast.success(`تم فتح ${r.created.length} تنبيه إعادة طلب.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الفحص')
    }
  }

  async function onAdjust(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await adjustStock({
        supplier_id: Number(adjust.supplier_id),
        product_id: Number(adjust.product_id),
        location_type: adjust.location_type,
        ...(adjust.location_id ? { location_id: Number(adjust.location_id) } : {}),
        delta: adjust.delta,
        ...(adjust.reorder_point ? { reorder_point: adjust.reorder_point } : {}),
      })
      toast.success('تم تعديل الرصيد وترحيل الحركة.')
      setAdjustOpen(false)
      setAdjust(EMPTY_ADJUST)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل التعديل')
    } finally {
      setBusy(false)
    }
  }

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-mono-body text-small transition-colors ${active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'}`

  const selectCls =
    'bg-transparent border-b border-surface-container-high py-2 font-body text-body focus:outline-none focus:border-primary'

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="أرصدة المخزون" subtitle={isAdmin ? 'مخزون كل مورد مستقل تمامًا.' : 'مخزونك الخاص.'} />
        {isAdmin && (
          <div className="flex gap-space-sm">
            <Button variant="secondary" onClick={onReorder} iconRight="notifications_active">فحص إعادة الطلب</Button>
            <Button variant="primary" onClick={() => { setAdjust(EMPTY_ADJUST); setAdjustOpen(true) }} iconRight="tune">تعديل رصيد</Button>
          </div>
        )}
      </div>

      <div className="mt-space-xl flex flex-wrap items-end gap-space-md">
        {isAdmin && <div className="w-40"><Field label="رقم المورد" dir="ltr" mono inputMode="numeric" value={supplierId} onChange={(e) => setSupplierId(e.target.value)} /></div>}
        <div className="flex gap-space-xs">
          {['', 'supplier', 'channel_partner', 'in_transit'].map((l) => (
            <button key={l || 'all'} className={chip(location === l)} onClick={() => setLocation(l)}>{l === '' ? 'كل المواقع' : LOC_AR[l]}</button>
          ))}
        </div>
        {isAdmin && <Button onClick={load}>تطبيق</Button>}
      </div>

      <div className="mt-space-lg">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(b) => b.id} empty="لا توجد أرصدة." columns={[
            { header: 'المنتج', cell: (b) => <Mono>{b.product_id}</Mono> },
            { header: 'الموقع', cell: (b) => <span className="font-body text-body">{LOC_AR[b.location_type] ?? b.location_type}</span> },
            { header: 'المتاح', align: 'end', cell: (b) => <Mono>{b.available}</Mono> },
            { header: 'المحجوز', align: 'end', cell: (b) => <Mono>{b.reserved}</Mono> },
            { header: 'حد إعادة الطلب', align: 'end', cell: (b) => <Mono>{b.reorder_point ?? '—'}</Mono> },
            { header: '', align: 'end', cell: (b) => (b.low ? <Pill tone="warning">منخفض</Pill> : null) },
          ]} />
        )}
      </div>

      {isAdmin && (
        <Modal open={adjustOpen} onClose={() => setAdjustOpen(false)} title="تعديل رصيد المخزون" footer={
          <>
            <Button onClick={() => setAdjustOpen(false)}>إلغاء</Button>
            <Button variant="primary" onClick={onAdjust} disabled={busy || !adjust.supplier_id || !adjust.product_id || !adjust.delta}>حفظ الحركة</Button>
          </>
        }>
          <form onSubmit={onAdjust} className="flex flex-col gap-space-md">
            <div className="grid grid-cols-2 gap-space-md">
              <Field label="رقم المورد" dir="ltr" mono inputMode="numeric" value={adjust.supplier_id} onChange={(e) => setAdjust({ ...adjust, supplier_id: e.target.value })} required />
              <Field label="رقم المنتج" dir="ltr" mono inputMode="numeric" value={adjust.product_id} onChange={(e) => setAdjust({ ...adjust, product_id: e.target.value })} required />
            </div>
            <div className="grid grid-cols-2 gap-space-md">
              <div className="flex flex-col">
                <label className="font-small text-small text-secondary mb-1">الموقع</label>
                <select className={selectCls} value={adjust.location_type} onChange={(e) => setAdjust({ ...adjust, location_type: e.target.value })}>
                  {LOC_TYPES.map((l) => <option key={l} value={l}>{LOC_AR[l]}</option>)}
                </select>
              </div>
              <Field label="رقم الموقع (اختياري)" dir="ltr" mono inputMode="numeric" value={adjust.location_id} onChange={(e) => setAdjust({ ...adjust, location_id: e.target.value })} />
            </div>
            <div className="grid grid-cols-2 gap-space-md">
              <Field label="التغيّر (+/−)" dir="ltr" mono inputMode="decimal" value={adjust.delta} onChange={(e) => setAdjust({ ...adjust, delta: e.target.value })} required hint="موجب للإضافة، سالب للخصم" />
              <Field label="حد إعادة الطلب (اختياري)" dir="ltr" mono inputMode="decimal" value={adjust.reorder_point} onChange={(e) => setAdjust({ ...adjust, reorder_point: e.target.value })} />
            </div>
          </form>
        </Modal>
      )}
    </Wide>
  )
}
