import { useMemo, useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { postManualJournal, type ManualJournalLine } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'
import { todayIso } from '../../lib/format'

function emptyLine(): ManualJournalLine {
  return { account_code: '', debit: '0', credit: '0' }
}

export function ManualJournalPage() {
  const toast = useToast()
  const [entryDate, setEntryDate] = useState<string>(todayIso())
  const [description, setDescription] = useState<string>('')
  const [reason, setReason] = useState<string>('')
  const [allowClosedPeriod, setAllowClosedPeriod] = useState<boolean>(false)
  const [lines, setLines] = useState<ManualJournalLine[]>([emptyLine(), emptyLine()])
  const [busy, setBusy] = useState<boolean>(false)
  const [result, setResult] = useState<{ entry_id: number; entry_no: string } | null>(null)

  const totalDebit = useMemo(
    () => lines.reduce((sum, l) => sum + (parseFloat(l.debit) || 0), 0),
    [lines],
  )
  const totalCredit = useMemo(
    () => lines.reduce((sum, l) => sum + (parseFloat(l.credit) || 0), 0),
    [lines],
  )
  const balanced = Math.abs(totalDebit - totalCredit) < 0.0001

  function setLine(i: number, next: Partial<ManualJournalLine>) {
    setLines((prev) => prev.map((l, idx) => (idx === i ? { ...l, ...next } : l)))
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!balanced) {
      toast.error('المجموع المدين لا يساوي الدائن.')
      return
    }
    setBusy(true)
    try {
      const resp = await postManualJournal({
        entry_date: entryDate,
        description,
        reason,
        allow_closed_period: allowClosedPeriod,
        lines,
      })
      setResult(resp)
      toast.success(`تم ترحيل القيد ${resp.entry_no}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل ترحيل القيد')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="قيد يدوي"
          subtitle="يتطلب صلاحية high.manual_journal — الوصف والسبب لا يقل عن 10 أحرف."
        />
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
            <Input
              label="تاريخ القيد"
              type="date"
              dir="ltr"
              value={entryDate}
              onChange={(e) => setEntryDate(e.target.value)}
              required
            />
            <div className="md:col-span-2">
              <Input
                label="الوصف"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                minLength={10}
                required
              />
            </div>
          </div>
          <Input
            label="السبب (يُسجَّل في Audit)"
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            minLength={10}
            required
          />
          <label className="inline-flex items-center gap-2 text-body text-ink">
            <input
              type="checkbox"
              checked={allowClosedPeriod}
              onChange={(e) => setAllowClosedPeriod(e.target.checked)}
            />
            السماح بالترحيل على فترة مُقفلة (يتطلب صلاحية إضافية)
          </label>

          <div className="mt-2 overflow-x-auto rounded-xl border border-warm-mist">
            <table className="min-w-full text-body">
              <thead className="bg-soft-paper">
                <tr>
                  <th className="px-3 py-2 text-start text-body-sm text-graphite">الحساب</th>
                  <th className="px-3 py-2 text-start text-body-sm text-graphite">مدين</th>
                  <th className="px-3 py-2 text-start text-body-sm text-graphite">دائن</th>
                  <th className="px-3 py-2 text-start text-body-sm text-graphite">تحليلي (اختياري)</th>
                  <th className="px-3 py-2 text-start text-body-sm text-graphite">وصف السطر</th>
                </tr>
              </thead>
              <tbody>
                {lines.map((l, i) => (
                  <tr key={i} className="border-t border-warm-mist">
                    <td className="px-2 py-2">
                      <input
                        className="w-28 rounded-md border border-warm-mist bg-parchment px-2 py-1 font-mono text-ink"
                        dir="ltr"
                        value={l.account_code}
                        onChange={(e) => setLine(i, { account_code: e.target.value })}
                        placeholder="1111"
                        required
                      />
                    </td>
                    <td className="px-2 py-2">
                      <input
                        className="w-32 rounded-md border border-warm-mist bg-parchment px-2 py-1 text-end font-mono text-ink"
                        dir="ltr"
                        value={l.debit}
                        onChange={(e) => setLine(i, { debit: e.target.value })}
                      />
                    </td>
                    <td className="px-2 py-2">
                      <input
                        className="w-32 rounded-md border border-warm-mist bg-parchment px-2 py-1 text-end font-mono text-ink"
                        dir="ltr"
                        value={l.credit}
                        onChange={(e) => setLine(i, { credit: e.target.value })}
                      />
                    </td>
                    <td className="px-2 py-2">
                      <input
                        className="w-40 rounded-md border border-warm-mist bg-parchment px-2 py-1 text-ink"
                        placeholder="supplier#7"
                        value={l.partner_type ? `${l.partner_type}#${l.partner_id ?? ''}` : ''}
                        onChange={(e) => {
                          const v = e.target.value.trim()
                          if (!v) {
                            setLine(i, { partner_type: undefined, partner_id: undefined })
                            return
                          }
                          const [t, id] = v.split('#')
                          setLine(i, {
                            partner_type: t ?? undefined,
                            partner_id: id ? Number(id) : undefined,
                          })
                        }}
                      />
                    </td>
                    <td className="px-2 py-2">
                      <input
                        className="w-full rounded-md border border-warm-mist bg-parchment px-2 py-1 text-ink"
                        value={l.description ?? ''}
                        onChange={(e) => setLine(i, { description: e.target.value })}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="flex items-center justify-between gap-3">
            <Button onClick={() => setLines((p) => [...p, emptyLine()])}>
              + سطر
            </Button>
            <div className="flex items-center gap-3 text-body text-ink">
              <span>مدين: <span className="font-mono">{totalDebit.toFixed(4)}</span></span>
              <span>دائن: <span className="font-mono">{totalCredit.toFixed(4)}</span></span>
              <Badge tone={balanced ? 'neutral' : 'muted'}>
                {balanced ? 'متوازن' : 'غير متوازن'}
              </Badge>
            </div>
          </div>

          <div className="flex justify-end">
            <Button variant="filled" type="submit" disabled={busy || !balanced}>
              {busy ? 'جار الترحيل…' : 'ترحيل القيد'}
            </Button>
          </div>
        </form>
      </Card>

      {result && (
        <Card elevated>
          <p className="text-body text-ink">
            رقم القيد:{' '}
            <code className="font-mono text-ink">{result.entry_no}</code> ·
            المعرّف <code className="font-mono">{result.entry_id}</code>
          </p>
        </Card>
      )}
    </div>
  )
}
