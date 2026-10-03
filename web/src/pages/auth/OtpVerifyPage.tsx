import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Button, Field, InlineError, Pill } from '../../components/ui'
import { verifyOtp } from '../../api/auth'
import { ApiError } from '../../api/client'

export function OtpVerifyPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const userId = Number(params.get('user_id') ?? '0')
  const channel = params.get('channel') ?? 'sms'
  const debug = params.get('debug') ?? ''
  const isSupplier = params.get('supplier') === '1'

  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    if (debug) setCode(debug)
  }, [debug])

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!userId) return
    setBusy(true)
    setError(null)
    try {
      const resp = await verifyOtp(userId, code)
      setStatus(resp.status)
      if (resp.status === 'active') setTimeout(() => navigate('/login'), 900)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout
      title="التحقق من الرمز"
      subtitle={channel === 'email' ? 'أرسلنا رمزًا على بريدك الإلكتروني.' : 'أرسلنا رمزًا على رقم هاتفك.'}
    >
      <form onSubmit={onSubmit} className="w-full flex flex-col gap-5">
        <Field label="الرمز" dir="ltr" mono inputMode="numeric" maxLength={10} value={code} onChange={(e) => setCode(e.target.value)} required />
        {debug && (
          <p className="font-small text-small text-secondary">
            رمز التطوير:{' '}
            <bdi dir="ltr" className="font-mono-medium text-on-surface">{debug}</bdi>
          </p>
        )}
        {status === 'pending' && isSupplier && (
          <p className="font-small text-small text-on-surface">
            تم التحقق بنجاح. حسابك كمورد <Pill tone="warning">قيد الاعتماد</Pill> من الإدارة.
          </p>
        )}
        {status === 'active' && (
          <p className="font-small text-small text-on-surface">تم التفعيل — سيتم تحويلك لتسجيل الدخول…</p>
        )}
        {error && <InlineError message={error} />}
        <Button variant="primary" type="submit" disabled={busy} className="w-full">
          {busy ? 'جار التحقق…' : 'تأكيد الرمز'}
        </Button>
      </form>
    </AuthLayout>
  )
}
