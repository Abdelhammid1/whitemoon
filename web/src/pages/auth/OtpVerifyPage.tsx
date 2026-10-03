import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { Badge } from '../../components/Badge'
import { verifyOtp } from '../../api/auth'
import { ApiError } from '../../api/client'

export function OtpVerifyPage() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const userId = Number(params.get('user_id') ?? '0')
  const channel = params.get('channel') ?? 'sms'
  const debug = params.get('debug') ?? ''
  const isSupplier = params.get('supplier') === '1'

  const [code, setCode] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<string | null>(null)

  useEffect(() => {
    if (debug) setCode(debug)
  }, [debug])

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    if (!userId) return
    setBusy(true)
    setError(null)
    try {
      const resp = await verifyOtp(userId, code)
      setStatus(resp.status)
      if (resp.status === 'active') {
        setTimeout(() => navigate('/login'), 800)
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <Card padding="lg">
        <CardHeader
          title="التحقق برمز OTP"
          subtitle={
            channel === 'email'
              ? 'أرسلنا رمزًا على بريدك الإلكتروني.'
              : 'أرسلنا رمزًا على رقم هاتفك.'
          }
        />
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Input
            label="الرمز"
            dir="ltr"
            inputMode="numeric"
            maxLength={10}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
          />
          {debug && (
            <div className="text-caption text-graphite">
              رمز التطوير: <span className="font-mono text-ink">{debug}</span>
            </div>
          )}

          {status === 'pending' && isSupplier && (
            <div className="rounded-xl border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
              تم التحقق بنجاح. حسابك كمورد <Badge tone="muted">قيد الاعتماد</Badge>{' '}
              من الإدارة. سنعلمك فور الموافقة.
            </div>
          )}
          {status === 'active' && (
            <div className="rounded-xl border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
              تم التفعيل بنجاح. سيتم تحويلك لتسجيل الدخول…
            </div>
          )}

          {error && (
            <div className="rounded-md border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
              {error}
            </div>
          )}
          <Button variant="filled" type="submit" disabled={busy}>
            {busy ? 'جار التحقق…' : 'تأكيد الرمز'}
          </Button>
        </form>
      </Card>
    </AuthLayout>
  )
}
