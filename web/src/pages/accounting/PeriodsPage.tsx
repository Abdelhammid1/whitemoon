import { useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { periodClose, periodEnsure, periodReopen } from '../../api/accounting'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'

export function PeriodsPage() {
  const toast = useToast()
  const now = new Date()
  const [year, setYear] = useState<number>(now.getFullYear())
  const [month, setMonth] = useState<number>(now.getMonth() + 1)
  const [state, setState] = useState<string>('—')
  const [busy, setBusy] = useState<boolean>(false)

  async function doAction(fn: () => Promise<unknown>, successMsg: string) {
    setBusy(true)
    try {
      await fn()
      toast.success(successMsg)
      setState('آخر عملية: ' + successMsg)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشلت العملية')
    } finally {
      setBusy(false)
    }
  }

  function onEnsure(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    void doAction(() => periodEnsure(year, month), `أُنشئت الفترة ${year}/${month} إن لم تكن موجودة`)
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="الفترات المحاسبية"
          subtitle="إنشاء / إقفال / إعادة فتح — إقفال فترة يرفض أي قيد جديد عليها (US-3.6)."
        />
        <form onSubmit={onEnsure} className="flex flex-wrap items-end gap-3">
          <div className="w-28">
            <Input
              label="السنة"
              dir="ltr"
              inputMode="numeric"
              value={String(year)}
              onChange={(e) => setYear(Number(e.target.value) || now.getFullYear())}
            />
          </div>
          <div className="w-28">
            <Input
              label="الشهر"
              dir="ltr"
              inputMode="numeric"
              value={String(month)}
              onChange={(e) => setMonth(Number(e.target.value) || 1)}
            />
          </div>
          <Button variant="filled" type="submit" disabled={busy}>
            إنشاء / تأكيد
          </Button>
          <Button
            onClick={() =>
              doAction(() => periodClose(year, month), `أُقفلت الفترة ${year}/${month}`)
            }
            disabled={busy}
          >
            إقفال
          </Button>
          <Button
            onClick={() =>
              doAction(() => periodReopen(year, month), `أُعيد فتح الفترة ${year}/${month}`)
            }
            disabled={busy}
          >
            إعادة فتح
          </Button>
        </form>
      </Card>

      <Card elevated>
        <div className="flex items-center justify-between gap-3">
          <span className="text-body-sm text-graphite">الحالة</span>
          <Badge tone="neutral">{state}</Badge>
        </div>
      </Card>

      <Card>
        <p className="text-body text-graphite">
          قاعدة البيانات ترفض فعليًا أي إدراج على <code className="font-mono text-ink">accounting.journal_lines</code>{' '}
          داخل فترة مُقفلة — إلا عبر مسار "قيد يدوي" بصلاحية{' '}
          <code className="font-mono text-ink">high.manual_journal.closed_period</code>.
        </p>
      </Card>
    </div>
  )
}
