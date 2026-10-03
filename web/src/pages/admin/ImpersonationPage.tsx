import { useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { startImpersonation, stopImpersonation } from '../../api/admin'
import { ApiError, tokenStore } from '../../api/client'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'

interface Active {
  grant_id: number
  acting_as_user_id: number
}

export function ImpersonationPage() {
  const toast = useToast()
  const { refresh } = useAuth()
  const [targetId, setTargetId] = useState<string>('')
  const [reason, setReason] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [active, setActive] = useState<Active | null>(null)
  const [originalToken, setOriginalToken] = useState<string | null>(null)

  async function onStart(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    const id = Number(targetId)
    if (!id) {
      toast.error('أدخل معرّف مستخدم صالح')
      return
    }
    if (reason.trim().length < 5) {
      toast.error('السبب يجب أن يكون 5 أحرف أو أكثر')
      return
    }
    setBusy(true)
    try {
      const resp = await startImpersonation(id, reason)
      setOriginalToken(tokenStore.getAccess())
      tokenStore.setAccess(resp.access_token)
      setActive({ grant_id: resp.grant_id, acting_as_user_id: resp.acting_as_user_id })
      await refresh()
      toast.success(`تم الدخول كمستخدم #${resp.acting_as_user_id}.`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل البدء')
    } finally {
      setBusy(false)
    }
  }

  async function onStop() {
    if (!active) return
    setBusy(true)
    try {
      await stopImpersonation(active.grant_id)
      // Restore the original admin token.
      if (originalToken) tokenStore.setAccess(originalToken)
      setActive(null)
      setOriginalToken(null)
      setTargetId('')
      setReason('')
      await refresh()
      toast.success('تم إنهاء التمثيل والعودة لحسابك.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الإنهاء')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="الدخول كمستخدم (Impersonation)"
          subtitle="للدعم الفني فقط. كل بدء وكل إنهاء يُسجَّل في سجل التدقيق."
        />
        {!active && (
          <form onSubmit={onStart} className="flex flex-col gap-3">
            <Input
              label="معرّف المستخدم المستهدف"
              dir="ltr"
              inputMode="numeric"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              required
            />
            <Input
              label="السبب (إلزامي، 5 أحرف فأكثر)"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              required
              minLength={5}
            />
            <div className="flex justify-end">
              <Button variant="filled" type="submit" disabled={busy}>
                {busy ? 'جار البدء…' : 'ابدأ'}
              </Button>
            </div>
          </form>
        )}

        {active && (
          <div className="flex flex-col gap-3">
            <div className="rounded-xl border border-warm-mist bg-soft-paper px-3 py-2 text-body text-ink">
              أنت الآن تعمل بصفة المستخدم رقم{' '}
              <span className="font-mono">{active.acting_as_user_id}</span>. منح رقم{' '}
              <span className="font-mono">{active.grant_id}</span>.
            </div>
            <div className="flex justify-end">
              <Button variant="filled" onClick={onStop} disabled={busy}>
                إنهاء والعودة لحسابي
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
