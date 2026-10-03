import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Field, Spinner, Button } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { reorderCheck, stockBalances, type StockBalance } from '../../api/inventory'
import { ApiError } from '../../api/client'

const LOC_AR: Record<string, string> = {
  supplier: 'مخزن المورد', channel_partner: 'عهدة وكيل/فرع', in_transit: 'في الطريق', customer_hold: 'حجز عميل',
}

export function StockPage() {
  const toast = useToast()
  const { user } = useAuth()
  const isAdmin = user?.kind === 'admin' || user?.kind === 'staff'
  const [supplierId, setSupplierId] = useState('')
  const [location, setLocation] = useState('')
  const [rows, setRows] = useState<StockBalance[]>([])
  const [loading, setLoading] = useState(true)

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

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-mono-body text-small transition-colors ${active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'}`

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="أرصدة المخزون" subtitle={isAdmin ? 'مخزون كل مورد مستقل تمامًا.' : 'مخزونك الخاص.'} />
        {isAdmin && <Button onClick={onReorder} iconRight="notifications_active">فحص إعادة الطلب</Button>}
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
    </Wide>
  )
}
