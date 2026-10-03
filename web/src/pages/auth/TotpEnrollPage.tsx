import { useState, type FormEvent } from 'react'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { totpEnrollFinish, totpEnrollStart, type TotpEnrollStart } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useToast } from '../../components/Toast'

export function TotpEnrollPage() {
  const [enrollment, setEnrollment] = useState<TotpEnrollStart | null>(null)
  const [code, setCode] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState<boolean>(false)
  const toast = useToast()

  async function startEnroll() {
    setBusy(true)
    setError(null)
    try {
      setEnrollment(await totpEnrollStart())
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  async function finishEnroll(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await totpEnrollFinish(code)
      setDone(true)
      toast.success('تم تفعيل التحقق الثنائي.')
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader
          title="التحقق الثنائي (2FA)"
          subtitle="إلزامي لحسابات الإدارة والوكلاء والموظفين."
        />
        {!enrollment && !done && (
          <div className="flex items-center gap-3">
            <Button variant="filled" onClick={startEnroll} disabled={busy}>
              {busy ? 'جار البدء…' : 'ابدأ الإعداد'}
            </Button>
            <p className="text-body-sm text-graphite">
              سيُنشأ لك سر TOTP + 8 رموز احتياطية تُستخدم مرة واحدة.
            </p>
          </div>
        )}

        {enrollment && !done && (
          <div className="flex flex-col gap-4">
            <div>
              <p className="text-body-sm text-graphite">المفتاح السري</p>
              <code className="mt-1 inline-block rounded-md border border-warm-mist bg-soft-paper px-2 py-1 text-body text-ink">
                {enrollment.secret}
              </code>
            </div>
            <div>
              <p className="text-body-sm text-graphite">
                رابط otpauth (اقرأه بتطبيق مثل Google Authenticator)
              </p>
              <code className="mt-1 block max-w-full truncate rounded-md border border-warm-mist bg-soft-paper px-2 py-1 text-body-sm text-ink">
                {enrollment.otpauth_uri}
              </code>
            </div>
            <div>
              <p className="text-body-sm text-graphite">الرموز الاحتياطية (احفظها الآن)</p>
              <div className="mt-1 grid grid-cols-2 gap-2 md:grid-cols-4">
                {enrollment.backup_codes.map((c) => (
                  <code
                    key={c}
                    className="rounded-md border border-warm-mist bg-soft-paper px-2 py-1 text-center text-body font-mono text-ink"
                  >
                    {c}
                  </code>
                ))}
              </div>
            </div>
            <form onSubmit={finishEnroll} className="flex flex-col gap-3">
              <Input
                label="أدخل رمز TOTP من تطبيقك لتأكيد الإعداد"
                dir="ltr"
                inputMode="numeric"
                maxLength={10}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
              />
              {error && (
                <div className="rounded-md border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
                  {error}
                </div>
              )}
              <Button variant="filled" type="submit" disabled={busy}>
                {busy ? 'جار التأكيد…' : 'تأكيد وتفعيل'}
              </Button>
            </form>
          </div>
        )}

        {done && (
          <div className="rounded-xl border border-warm-mist bg-soft-paper px-3 py-2 text-body text-ink">
            تم التفعيل بنجاح. سيُطلب رمز TOTP في كل مرة تدخل فيها.
          </div>
        )}
      </Card>
    </div>
  )
}
