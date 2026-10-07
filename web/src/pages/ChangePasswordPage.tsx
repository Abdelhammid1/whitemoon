import { useState, type FormEvent } from 'react'
import { Narrow } from '../layouts/AppShell'
import { PageTitle, Button, Field, Card, InlineError } from '../components/ui'
import { PageHelp } from '../components/PageHelp'
import { useToast } from '../components/Toast'
import { changePassword } from '../api/auth'
import { ApiError } from '../api/client'

/** Self-service password change — available to every signed-in user. */
export function ChangePasswordPage() {
  const toast = useToast()
  const [current, setCurrent] = useState('')
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const tooShort = next.length > 0 && next.length < 8
  const mismatch = confirm.length > 0 && next !== confirm
  const canSubmit = current.length > 0 && next.length >= 8 && next === confirm && !busy

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (!canSubmit) return
    setBusy(true)
    try {
      await changePassword(current, next)
      toast.success('تم تغيير كلمة المرور. سُجّل الخروج من الأجهزة الأخرى.')
      setCurrent(''); setNext(''); setConfirm('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر تغيير كلمة المرور')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <PageTitle title="تغيير كلمة المرور" subtitle="حدّث كلمة مرورك في أي وقت" />
      <PageHelp pageKey="change-password" />
      <Card className="mt-space-lg">
        <form onSubmit={onSubmit} className="flex flex-col gap-space-md">
          <Field
            label="كلمة المرور الحالية"
            type="password"
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
            autoComplete="current-password"
          />
          <Field
            label="كلمة المرور الجديدة"
            type="password"
            value={next}
            onChange={(e) => setNext(e.target.value)}
            autoComplete="new-password"
            hint={tooShort ? <span className="text-danger">٨ أحرف على الأقل</span> : '٨ أحرف على الأقل'}
          />
          <Field
            label="تأكيد كلمة المرور الجديدة"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
            hint={mismatch ? <span className="text-danger">غير متطابقة</span> : undefined}
          />
          {error && <InlineError message={error} />}
          <div className="flex justify-end">
            <Button variant="primary" type="submit" disabled={!canSubmit}>
              {busy ? 'جارٍ الحفظ…' : 'تغيير كلمة المرور'}
            </Button>
          </div>
        </form>
      </Card>
    </Narrow>
  )
}
