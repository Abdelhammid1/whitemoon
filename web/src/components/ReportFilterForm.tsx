import { useState, type FormEvent } from 'react'
import { Input } from './Input'
import { Button } from './Button'
import type { ReportFilterBody } from '../api/accounting'

interface Props {
  onRun: (filter: ReportFilterBody) => Promise<void>
  showPartner?: boolean
  showAccountPrefix?: boolean
  busy?: boolean
}

export function ReportFilterForm({
  onRun,
  showPartner = true,
  showAccountPrefix = true,
  busy = false,
}: Props) {
  const now = new Date()
  const first = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
  const last = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
  const [dateFrom, setDateFrom] = useState<string>(first)
  const [dateTo, setDateTo] = useState<string>(last)
  const [accountPrefix, setAccountPrefix] = useState<string>('')
  const [partnerType, setPartnerType] = useState<string>('')
  const [partnerId, setPartnerId] = useState<string>('')

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    await onRun({
      date_from: dateFrom,
      date_to: dateTo,
      account_prefix: accountPrefix || undefined,
      partner_type: partnerType || undefined,
      partner_id: partnerId ? Number(partnerId) : undefined,
    })
  }

  return (
    <form onSubmit={onSubmit} className="flex flex-wrap items-end gap-3">
      <div className="w-44">
        <Input
          label="من تاريخ"
          type="date"
          dir="ltr"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
          required
        />
      </div>
      <div className="w-44">
        <Input
          label="إلى تاريخ"
          type="date"
          dir="ltr"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
          required
        />
      </div>
      {showAccountPrefix && (
        <div className="w-32">
          <Input
            label="بادئة الحساب"
            dir="ltr"
            placeholder="11"
            value={accountPrefix}
            onChange={(e) => setAccountPrefix(e.target.value)}
          />
        </div>
      )}
      {showPartner && (
        <>
          <div className="w-40">
            <Input
              label="نوع الطرف"
              dir="ltr"
              placeholder="supplier"
              value={partnerType}
              onChange={(e) => setPartnerType(e.target.value)}
            />
          </div>
          <div className="w-32">
            <Input
              label="رقم الطرف"
              dir="ltr"
              inputMode="numeric"
              value={partnerId}
              onChange={(e) => setPartnerId(e.target.value)}
            />
          </div>
        </>
      )}
      <Button variant="filled" type="submit" disabled={busy}>
        {busy ? 'جار التشغيل…' : 'تشغيل التقرير'}
      </Button>
    </form>
  )
}
