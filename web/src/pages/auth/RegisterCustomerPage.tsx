import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { registerCustomer } from '../../api/auth'
import { ApiError } from '../../api/client'

export function RegisterCustomerPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = useState<string>('')
  const [email, setEmail] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const [displayName, setDisplayName] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const resp = await registerCustomer({
        phone: phone || undefined,
        email: email || undefined,
        password,
        display_name: displayName,
      })
      navigate(
        `/otp?user_id=${resp.user_id}&channel=${encodeURIComponent(resp.otp.channel)}&debug=${encodeURIComponent(resp.otp.debug_code ?? '')}`,
      )
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <Card>
        <CardHeader
          title="حساب عميل جديد"
          subtitle="يفعّل حسابك فور التحقق من رقم الهاتف."
        />
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Input
            label="الاسم الظاهر"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            required
            maxLength={200}
          />
          <Input
            label="رقم الهاتف"
            type="tel"
            dir="ltr"
            placeholder="+2010XXXXXXXX"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            autoComplete="tel"
            hint="اكتب الهاتف أو البريد — الأفضل الاثنين."
          />
          <Input
            label="البريد الإلكتروني (اختياري)"
            type="email"
            dir="ltr"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <Input
            label="كلمة المرور"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            autoComplete="new-password"
          />
          {error && (
            <div className="rounded-md border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
              {error}
            </div>
          )}
          <Button variant="filled" type="submit" disabled={busy}>
            {busy ? 'جار الإنشاء…' : 'إنشاء الحساب'}
          </Button>
          <div className="text-body-sm text-graphite">
            <Link to="/login" className="hover:text-ink">
              لديك حساب؟ تسجيل الدخول
            </Link>
          </div>
        </form>
      </Card>
    </AuthLayout>
  )
}
