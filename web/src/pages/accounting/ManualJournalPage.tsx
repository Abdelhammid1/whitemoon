import { useMemo, useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, InlineError, Card } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { useToast } from '../../components/Toast'
import { postManualJournal, type ManualJournalLine } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { PageHelp } from '../../components/PageHelp'
import { todayIso } from '../../lib/format'

const emptyLine = (): ManualJournalLine => ({ account_code: '', debit: '0', credit: '0' })

export function ManualJournalPage() {
  const toast = useToast()
  const [entryDate, setEntryDate] = useState(todayIso())
  const [description, setDescription] = useState('')
  const [reason, setReason] = useState('')
  const [allowClosed, setAllowClosed] = useState(false)
  const [lines, setLines] = useState<ManualJournalLine[]>([emptyLine(), emptyLine()])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<{ entry_no: string } | null>(null)

  const totalDebit = useMemo(() => lines.reduce((s, l) => s + (parseFloat(l.debit) || 0), 0), [lines])
  const totalCredit = useMemo(() => lines.reduce((s, l) => s + (parseFloat(l.credit) || 0), 0), [lines])
  const balanced = Math.abs(totalDebit - totalCredit) < 0.0001

  const setLine = (i: number, next: Partial<ManualJournalLine>) =>
    setLines((p) => p.map((l, idx) => (idx === i ? { ...l, ...next } : l)))

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!balanced) return setError('المجموع المدين لا يساوي الدائن.')
    setBusy(true)
    try {
      const resp = await postManualJournal({ entry_date: entryDate, description, reason, allow_closed_period: allowClosed, lines })
      setResult(resp)
      toast.success(`تم ترحيل القيد ${resp.entry_no}.`)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'فشل ترحيل القيد')
    } finally {
      setBusy(false)
    }
  }

  const cell = 'w-full bg-transparent border-b border-surface-container-high focus:border-primary focus:border-b-2 focus:outline-none py-1 font-mono-body text-mono-body text-on-surface'

  return (
    <Narrow>
      <PageTitle title="إنشاء قيد يومية يدوي" subtitle="يتطلب صلاحية قيد يدوي — الوصف والسبب لا يقل كل منهما عن ١٠ أحرف." />

      <PageHelp pageKey="manual-journal" />

      <form onSubmit={onSubmit} className="mt-space-xl flex flex-col gap-space-lg">
        <Card className="flex flex-col gap-space-md">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-space-md">
            <Field label="تاريخ القيد" type="date" dir="ltr" value={entryDate} onChange={(e) => setEntryDate(e.target.value)} required />
            <div className="md:col-span-2"><Field label="الوصف / البيان العام" value={description} onChange={(e) => setDescription(e.target.value)} minLength={10} required /></div>
          </div>
          <Field label="السبب (يُسجَّل في التدقيق)" value={reason} onChange={(e) => setReason(e.target.value)} minLength={10} required />

          <label className="flex items-center gap-space-sm font-body text-body text-on-surface">
            <input type="checkbox" checked={allowClosed} onChange={(e) => setAllowClosed(e.target.checked)} />
            السماح بالترحيل على فترة مُقفلة (يتطلب صلاحية إضافية)
          </label>
        </Card>

        <Card padded={false} className="flex flex-col gap-space-md p-space-lg">
          <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="bg-surface-container-low border-b border-surface-container-high">
                <th className="px-space-sm py-space-sm text-start font-small text-small text-secondary">كود الحساب</th>
                <th className="px-space-sm py-space-sm text-start font-small text-small text-secondary">مدين</th>
                <th className="px-space-sm py-space-sm text-start font-small text-small text-secondary">دائن</th>
                <th className="px-space-sm py-space-sm text-start font-small text-small text-secondary">البيان التفصيلي</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((l, i) => (
                <tr key={i} className="border-b border-surface-container-high">
                  <td className="px-space-sm py-space-sm"><input dir="ltr" className={cell} placeholder="1111" value={l.account_code} onChange={(e) => setLine(i, { account_code: e.target.value })} required /></td>
                  <td className="px-space-sm py-space-sm"><input dir="ltr" className={`${cell} text-end`} value={l.debit} onChange={(e) => setLine(i, { debit: e.target.value })} /></td>
                  <td className="px-space-sm py-space-sm"><input dir="ltr" className={`${cell} text-end`} value={l.credit} onChange={(e) => setLine(i, { credit: e.target.value })} /></td>
                  <td className="px-space-sm py-space-sm"><input className={cell.replace('font-mono-body text-mono-body', 'font-body text-body')} value={l.description ?? ''} onChange={(e) => setLine(i, { description: e.target.value })} /></td>
                </tr>
              ))}
            </tbody>
          </table>
          </div>

          <div className="flex items-center justify-between flex-wrap gap-space-md border-t border-surface-container-high pt-space-md">
            <Button onClick={() => setLines((p) => [...p, emptyLine()])}>+ إضافة طرف قيد</Button>
            <div className="flex items-center gap-space-md font-mono-body text-mono-body text-on-surface">
              <span>مدين: <bdi dir="ltr">{totalDebit.toFixed(2)}</bdi></span>
              <span>دائن: <bdi dir="ltr">{totalCredit.toFixed(2)}</bdi></span>
              <Pill tone={balanced ? 'signal' : 'error'}>{balanced ? 'متوازن' : 'غير متوازن'}</Pill>
            </div>
          </div>
        </Card>

        {error && <InlineError message={error} />}
        <div className="flex justify-end">
          <Button variant="primary" type="submit" iconRight="check_circle" disabled={busy || !balanced}>
            {busy ? 'جار الترحيل…' : 'ترحيل واعتماد القيد'}
          </Button>
        </div>
      </form>

      {result && (
        <Card className="mt-space-lg flex items-center gap-space-md">
          <span className="w-10 h-10 rounded-xl bg-signal-weak text-signal flex items-center justify-center shrink-0">
            <Icon name="check_circle" size={20} />
          </span>
          <span className="font-body text-body text-on-surface">
            تم ترحيل القيد رقم <bdi dir="ltr" className="font-mono-medium">{result.entry_no}</bdi>
          </span>
        </Card>
      )}
    </Narrow>
  )
}
