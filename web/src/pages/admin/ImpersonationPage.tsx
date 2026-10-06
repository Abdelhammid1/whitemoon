import { useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, InlineError, Card, Pill } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { PageHelp } from '../../components/PageHelp'
import { startImpersonation } from '../../api/admin'
import { ApiError, tokenStore } from '../../api/client'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { getImpersonation, setImpersonation } from '../../auth/impersonation'

export function ImpersonationPage() {
  const toast = useToast()
  const { refresh } = useAuth()
  const [targetId, setTargetId] = useState('')
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const active = getImpersonation()

  async function onStart(e: FormEvent) {
    e.preventDefault()
    setError(null)
    const id = Number(targetId)
    if (!id) return setError('أدخل معرّف مستخدم صالح')
    if (reason.trim().length < 5) return setError('السبب يجب أن يكون ٥ أحرف أو أكثر')
    setBusy(true)
    try {
      const adminToken = tokenStore.getAccess() ?? ''
      const resp = await startImpersonation(id, reason)
      tokenStore.setAccess(resp.access_token)
      setImpersonation({
        grant_id: resp.grant_id,
        acting_as_user_id: resp.acting_as_user_id,
        admin_token: adminToken,
        started_at: Date.now(),
      })
      await refresh()
      toast.success(`تم الدخول بصفة المستخدم #${resp.acting_as_user_id}.`)
      setTargetId('')
      setReason('')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'فشل البدء')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <PageTitle title="الدخول كمستخدم (Impersonation)" subtitle="للدعم الفني فقط. كل بدء وإنهاء يُسجَّل في سجل التدقيق." />

      <PageHelp pageKey="impersonation" />

      <Card className="mt-space-xl flex items-start gap-space-md border-warning/40">
        <span className="w-10 h-10 rounded-xl bg-warning-weak flex items-center justify-center shrink-0">
          <Icon name="warning" size={20} className="text-warning" />
        </span>
        <div className="flex flex-col gap-space-xs min-w-0">
          <div className="flex items-center gap-space-sm">
            <span className="font-body-medium text-body-medium text-on-surface">صلاحية حسّاسة</span>
            <Pill tone="warning">يُسجَّل بالكامل</Pill>
          </div>
          <p className="font-body text-body text-secondary">
            عند بدء الجلسة ستتصرّف نيابةً عن المستخدم المستهدف داخل المنظومة. يُوثَّق المنفِّذ والهدف والسبب والوقت في سجل التدقيق. لا تُستخدم إلا لأغراض الدعم الفني المصرَّح بها.
          </p>
        </div>
      </Card>

      <div className="mt-space-lg">
        {active ? (
          <Card className="flex items-start gap-space-md border-danger/40">
            <span className="w-10 h-10 rounded-xl bg-danger-weak flex items-center justify-center shrink-0">
              <Icon name="person" size={20} className="text-danger" />
            </span>
            <div className="flex flex-col gap-space-xs min-w-0">
              <div className="flex items-center gap-space-sm">
                <span className="font-body-medium text-body-medium text-on-surface">جلسة تمثيل نشطة</span>
                <Pill tone="error">نشطة الآن</Pill>
              </div>
              <p className="font-body text-body text-secondary">
                أنت تتصرّف حالياً بصفة المستخدم{' '}
                <bdi dir="ltr" className="font-mono-medium text-on-surface">#{active.acting_as_user_id}</bdi>. استخدم الشريط العلوي لإنهاء الجلسة.
              </p>
            </div>
          </Card>
        ) : (
          <Card>
            <form onSubmit={onStart} className="flex flex-col gap-space-lg max-w-[420px]">
              <Field label="معرّف المستخدم المستهدف" dir="ltr" mono inputMode="numeric" value={targetId} onChange={(e) => setTargetId(e.target.value)} required />
              <Field label="السبب (إلزامي، ٥ أحرف فأكثر)" value={reason} onChange={(e) => setReason(e.target.value)} required minLength={5} />
              {error && <InlineError message={error} />}
              <div><Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار البدء…' : 'بدء الجلسة'}</Button></div>
            </form>
          </Card>
        )}
      </div>
    </Narrow>
  )
}
