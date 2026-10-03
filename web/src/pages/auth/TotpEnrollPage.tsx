import { useState, type FormEvent } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Narrow } from '../../layouts/AppShell'
import { Button, Field, InlineError, PageTitle } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { totpEnrollFinish, totpEnrollStart, type TotpEnrollStart } from '../../api/auth'
import { ApiError } from '../../api/client'

export function TotpEnrollPage() {
  const [enrollment, setEnrollment] = useState<TotpEnrollStart | null>(null)
  const [code, setCode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [done, setDone] = useState(false)

  async function start() {
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

  async function finish(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await totpEnrollFinish(code)
      setDone(true)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  function downloadBackups() {
    if (!enrollment) return
    const blob = new Blob([enrollment.backup_codes.join('\n')], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'white-moon-backup-codes.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  const step = 'font-small-medium text-small-medium text-secondary mb-space-sm'

  return (
    <Narrow>
      <PageTitle title="التحقق الثنائي (2FA)" subtitle="إلزامي لحسابات الإدارة والوكلاء والموظفين." />

      <div className="mt-[48px] flex flex-col gap-space-xl">
        {!enrollment && !done && (
          <div className="flex items-center gap-space-md">
            <Button variant="primary" onClick={start} disabled={busy}>
              {busy ? 'جار البدء…' : 'ابدأ الإعداد'}
            </Button>
            <p className="font-body text-body text-secondary">
              سيُنشأ لك سر TOTP + 8 رموز احتياطية تُستخدم مرة واحدة.
            </p>
          </div>
        )}

        {enrollment && !done && (
          <>
            <div className="flex flex-col">
              <p className={step}>١. امسح الرمز بتطبيق مثل Google Authenticator</p>
              <div className="flex items-start gap-space-xl">
                <div className="p-space-md border border-surface-container-high rounded-xl bg-surface-container-lowest">
                  <QRCodeSVG value={enrollment.otpauth_uri} size={132} />
                </div>
                <div className="flex flex-col gap-space-xs">
                  <span className="font-small text-small text-secondary">أو أدخل المفتاح يدويًا:</span>
                  <bdi dir="ltr" className="font-mono-medium text-mono-medium text-on-surface break-all">
                    {enrollment.secret}
                  </bdi>
                </div>
              </div>
            </div>

            <div className="flex flex-col">
              <div className="flex items-center justify-between mb-space-sm">
                <p className={`${step} mb-0`}>٢. احفظ الرموز الاحتياطية</p>
                <button onClick={downloadBackups} className="font-small text-small text-secondary hover:text-primary underline underline-offset-4">
                  <Icon name="download" size={16} /> تنزيل كملف
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-space-sm">
                {enrollment.backup_codes.map((c) => (
                  <bdi key={c} dir="ltr" className="font-mono-body text-mono-body text-on-surface text-center py-space-xs border-b border-surface-container-high">
                    {c}
                  </bdi>
                ))}
              </div>
            </div>

            <form onSubmit={finish} className="flex flex-col gap-space-md max-w-[320px]">
              <p className={step}>٣. أكد الإعداد برمز من تطبيقك</p>
              <Field label="رمز TOTP" dir="ltr" mono inputMode="numeric" maxLength={10} value={code} onChange={(e) => setCode(e.target.value)} required />
              {error && <InlineError message={error} />}
              <Button variant="primary" type="submit" disabled={busy}>
                {busy ? 'جار التأكيد…' : 'تأكيد وتفعيل'}
              </Button>
            </form>
          </>
        )}

        {done && (
          <p className="font-body text-body text-on-surface">
            تم التفعيل بنجاح. سيُطلب رمز TOTP في كل مرة تدخل فيها.
          </p>
        )}
        {!enrollment && error && <InlineError message={error} />}
      </div>
    </Narrow>
  )
}
