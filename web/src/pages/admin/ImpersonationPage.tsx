import { useState, type FormEvent } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, InlineError } from '../../components/ui'
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
      <div className="mt-space-xl">
        {active ? (
          <p className="font-body text-body text-on-surface">
            جلسة تمثيل نشطة للمستخدم{' '}
            <bdi dir="ltr" className="font-mono-medium">#{active.acting_as_user_id}</bdi>. استخدم الشريط العلوي لإنهائها.
          </p>
        ) : (
          <form onSubmit={onStart} className="flex flex-col gap-space-lg max-w-[420px]">
            <Field label="معرّف المستخدم المستهدف" dir="ltr" mono inputMode="numeric" value={targetId} onChange={(e) => setTargetId(e.target.value)} required />
            <Field label="السبب (إلزامي، ٥ أحرف فأكثر)" value={reason} onChange={(e) => setReason(e.target.value)} required minLength={5} />
            {error && <InlineError message={error} />}
            <div><Button variant="primary" type="submit" disabled={busy}>{busy ? 'جار البدء…' : 'بدء الجلسة'}</Button></div>
          </form>
        )}
      </div>
    </Narrow>
  )
}
