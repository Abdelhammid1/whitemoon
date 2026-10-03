import { useState, type FormEvent } from 'react'
import { Field, Button } from './ui'
import type { ReportFilterBody } from '../api/accounting'

interface Props {
  onRun: (filter: ReportFilterBody) => Promise<void>
  showPartner?: boolean
  showAccountPrefix?: boolean
  busy?: boolean
}

export function ReportFilterForm({ onRun, showPartner = true, showAccountPrefix = true, busy = false }: Props) {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
  const [dateFrom, setDateFrom] = useState(first)
  const [dateTo, setDateTo] = useState(last)
  const [prefix, setPrefix] = useState('')
  const [partnerType, setPartnerType] = useState('')
  const [partnerId, setPartnerId] = useState('')

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    await onRun({
      date_from: dateFrom,
      date_to: dateTo,
      account_prefix: prefix || undefined,
      partner_type: partnerType || undefined,
      partner_id: partnerId ? Number(partnerId) : undefined,
    })
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-space-md">
      <div className="w-44"><Field label="من تاريخ" type="date" dir="ltr" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} required /></div>
      <div className="w-44"><Field label="إلى تاريخ" type="date" dir="ltr" value={dateTo} onChange={(e) => setDateTo(e.target.value)} required /></div>
      {showAccountPrefix && <div className="w-32"><Field label="بادئة الحساب" dir="ltr" mono placeholder="11" value={prefix} onChange={(e) => setPrefix(e.target.value)} /></div>}
      {showPartner && (
        <>
          <div className="w-40"><Field label="نوع الطرف" dir="ltr" placeholder="supplier" value={partnerType} onChange={(e) => setPartnerType(e.target.value)} /></div>
          <div className="w-32"><Field label="رقم الطرف" dir="ltr" mono inputMode="numeric" value={partnerId} onChange={(e) => setPartnerId(e.target.value)} /></div>
        </>
      )}
      <Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار التشغيل…' : 'تشغيل التقرير'}</Button>
    </form>
  )
}
