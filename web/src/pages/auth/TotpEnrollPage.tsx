import { useState, type FormEvent } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import { Narrow } from '../../layouts/AppShell'
import { Button, Card, Field, InlineError, PageTitle, Pill } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { PageHelp } from '../../components/PageHelp'
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

  const stepHead = (n: string, text: string) => (
    <div className="flex items-center gap-space-sm">
      <span className="w-7 h-7 rounded-pill bg-brand-weak text-primary font-mono-medium text-mono-medium flex items-center justify-center shrink-0">
        {n}
      </span>
      <span className="font-headline-2 text-headline-2 text-on-surface font-medium">{text}</span>
    </div>
  )

  return (
    <Narrow>
      <PageTitle title="التحقق الثنائي (2FA)" subtitle="إلزامي لحسابات الإدارة والوكلاء والموظفين." />

      <PageHelp pageKey="totp-enroll" />

      <div className="mt-space-xl flex flex-col gap-space-lg">
        {!enrollment && !done && (
          <Card className="flex flex-col gap-space-md">
            <span className="w-11 h-11 rounded-xl bg-gold-weak flex items-center justify-center">
              <Icon name="encrypted" size={22} className="text-gold" />
            </span>
            <div className="flex flex-col gap-space-xs">
              <h2 className="font-headline-2 text-headline-2 text-on-surface font-medium">تفعيل التحقق الثنائي</h2>
              <p className="font-body text-body text-secondary">
                سيُنشأ لك سر TOTP + 8 رموز احتياطية تُستخدم مرة واحدة.
              </p>
            </div>
            <div>
              <Button variant="primary" onClick={start} disabled={busy} iconRight="arrow_left_alt">
                {busy ? 'جار البدء…' : 'ابدأ الإعداد'}
              </Button>
            </div>
            {error && <InlineError message={error} />}
          </Card>
        )}

        {enrollment && !done && (
          <>
            <Card className="flex flex-col gap-space-md">
              {stepHead('١', 'امسح الرمز بتطبيق مثل Google Authenticator')}
              <div className="flex flex-col sm:flex-row items-start gap-space-lg">
                <div className="p-space-md border border-surface-container-high rounded-xl bg-surface-container-lowest shrink-0">
                  <QRCodeSVG value={enrollment.otpauth_uri} size={132} />
                </div>
                <div className="flex flex-col gap-space-xs">
                  <span className="font-small text-small text-secondary">أو أدخل المفتاح يدويًا:</span>
                  <bdi dir="ltr" className="font-mono-medium text-mono-medium text-on-surface break-all rounded-lg bg-surface-container-low px-space-md py-space-sm">
                    {enrollment.secret}
                  </bdi>
                </div>
              </div>
            </Card>

            <Card className="flex flex-col gap-space-md">
              <div className="flex items-center justify-between gap-space-sm">
                {stepHead('٢', 'احفظ الرموز الاحتياطية')}
                <button onClick={downloadBackups} className="inline-flex items-center gap-space-xs font-small-medium text-small-medium text-secondary hover:text-primary transition-colors shrink-0">
                  <Icon name="download" size={16} /> تنزيل كملف
                </button>
              </div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-space-xs rounded-xl bg-surface-container-low p-space-md">
                {enrollment.backup_codes.map((c) => (
                  <bdi key={c} dir="ltr" className="font-mono-body text-mono-body text-on-surface text-center py-space-xs">
                    {c}
                  </bdi>
                ))}
              </div>
            </Card>

            <Card>
              <form onSubmit={finish} className="flex flex-col gap-space-md max-w-[320px]">
                {stepHead('٣', 'أكد الإعداد برمز من تطبيقك')}
                <Field label="رمز TOTP" dir="ltr" mono inputMode="numeric" maxLength={10} value={code} onChange={(e) => setCode(e.target.value)} required />
                {error && <InlineError message={error} />}
                <Button variant="primary" type="submit" disabled={busy}>
                  {busy ? 'جار التأكيد…' : 'تأكيد وتفعيل'}
                </Button>
              </form>
            </Card>
          </>
        )}

        {done && (
          <Card className="flex items-start gap-space-md">
            <span className="w-11 h-11 rounded-xl bg-signal-weak flex items-center justify-center shrink-0">
              <Icon name="task_alt" size={22} className="text-signal" />
            </span>
            <div className="flex flex-col gap-space-xs">
              <div className="flex items-center gap-space-sm">
                <h2 className="font-headline-2 text-headline-2 text-on-surface font-medium">تم التفعيل بنجاح</h2>
                <Pill tone="signal">مُفعَّل</Pill>
              </div>
              <p className="font-body text-body text-secondary">سيُطلب رمز TOTP في كل مرة تدخل فيها.</p>
            </div>
          </Card>
        )}
      </div>
    </Narrow>
  )
}
