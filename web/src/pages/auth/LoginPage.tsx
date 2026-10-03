import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { Chip } from '../../components/Chip'
import { login } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'
import { useToast } from '../../components/Toast'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { refresh } = useAuth()
  const toast = useToast()
  const [identifier, setIdentifier] = useState<'phone' | 'email'>('phone')
  const [phone, setPhone] = useState<string>('')
  const [email, setEmail] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const [totpCode, setTotpCode] = useState<string>('')
  const [requires2fa, setRequires2fa] = useState<boolean>(false)
  const [busy, setBusy] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/'

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const resp = await login({
        ...(identifier === 'phone' ? { phone } : { email }),
        password,
        ...(requires2fa && totpCode ? { totp_code: totpCode } : {}),
      })
      if (resp.requires_2fa) {
        setRequires2fa(true)
        toast.info('أدخل رمز التحقق الثنائي من تطبيق المصادقة.')
        return
      }
      await refresh()
      navigate(from, { replace: true })
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('حدث خطأ غير متوقع')
      }
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthLayout>
      <Card>
        <CardHeader title="تسجيل الدخول" subtitle="وايت مون — منصة الأعمال" />
        <form onSubmit={onSubmit} className="flex flex-col gap-4">
          <div className="flex gap-2">
            <Chip
              active={identifier === 'phone'}
              onClick={() => setIdentifier('phone')}
            >
              رقم الهاتف
            </Chip>
            <Chip
              active={identifier === 'email'}
              onClick={() => setIdentifier('email')}
            >
              البريد الإلكتروني
            </Chip>
          </div>

          {identifier === 'phone' ? (
            <Input
              label="رقم الهاتف"
              type="tel"
              dir="ltr"
              placeholder="+2010XXXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              autoComplete="tel"
              required
            />
          ) : (
            <Input
              label="البريد الإلكتروني"
              type="email"
              dir="ltr"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          )}

          <Input
            label="كلمة المرور"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />

          {requires2fa && (
            <Input
              label="رمز التحقق الثنائي (6 أرقام)"
              dir="ltr"
              inputMode="numeric"
              maxLength={10}
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value)}
              required
            />
          )}

          {error && (
            <div className="rounded-md border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
              {error}
            </div>
          )}

          <Button variant="filled" type="submit" disabled={busy}>
            {busy ? 'جار الدخول…' : 'دخول'}
          </Button>

          <div className="flex items-center justify-between text-body-sm text-graphite">
            <Link to="/register" className="hover:text-ink">
              حساب عميل جديد
            </Link>
            <Link to="/register/supplier" className="hover:text-ink">
              تسجيل مورد
            </Link>
          </div>
        </form>
      </Card>
    </AuthLayout>
  )
}
