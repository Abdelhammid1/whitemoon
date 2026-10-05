import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Button, Field, InlineError } from '../../components/ui'
import { login } from '../../api/auth'
import { ApiError } from '../../api/client'
import { useAuth } from '../../auth/AuthContext'

export function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const { refresh } = useAuth()
  const [mode, setMode] = useState<'phone' | 'email'>('phone')
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [totp, setTotp] = useState('')
  const [requires2fa, setRequires2fa] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/'

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const resp = await login({
        ...(mode === 'phone' ? { phone: identifier } : { email: identifier }),
        password,
        ...(requires2fa && totp ? { totp_code: totp } : {}),
      })
      if (resp.requires_2fa) {
        setRequires2fa(true)
        return
      }
      await refresh()
      navigate(from, { replace: true })
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'حدث خطأ غير متوقع')
    } finally {
      setBusy(false)
    }
  }

  const tab = (active: boolean) =>
    `font-small-medium text-small-medium pb-2 transition-all border-b-2 ${
      active ? 'text-on-surface border-primary' : 'text-secondary border-transparent hover:text-on-surface'
    }`

  return (
    <AuthLayout
      title="تسجيل الدخول للنظام"
      subtitle="منصة وايت مون للأعمال والتجارة B2B"
      footerLinks={
        <>
          <Link to="/register" className="hover:text-on-surface">حساب عميل جديد</Link>
          <span className="text-outline-variant">·</span>
          <Link to="/register/supplier" className="hover:text-on-surface">تسجيل كمورد تجاري</Link>
        </>
      }
    >
      <div className="w-full flex items-center justify-start gap-space-lg border-b border-surface-container-high mb-space-lg">
        <button type="button" className={tab(mode === 'phone')} onClick={() => setMode('phone')}>
          رقم الهاتف
        </button>
        <button type="button" className={tab(mode === 'email')} onClick={() => setMode('email')}>
          البريد الإلكتروني
        </button>
      </div>

      <form onSubmit={onSubmit} className="w-full flex flex-col gap-space-md">
        <Field
          label={mode === 'phone' ? 'رقم الهاتف المسجل' : 'البريد الإلكتروني التجاري'}
          dir="ltr"
          mono={mode === 'phone'}
          type={mode === 'phone' ? 'tel' : 'email'}
          placeholder={mode === 'phone' ? '+20 100 000 0000' : 'enterprise@domain.com.eg'}
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          required
        />
        <Field
          label="كلمة المرور"
          type="password"
          placeholder="••••••••"
          mono
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        {requires2fa && (
          <Field
            label="رمز التحقق الثنائي"
            dir="ltr"
            mono
            inputMode="numeric"
            maxLength={10}
            value={totp}
            onChange={(e) => setTotp(e.target.value)}
            required
          />
        )}
        {error && <InlineError message={error} />}
        <Button variant="primary" type="submit" disabled={busy} iconRight="arrow_left_alt" className="w-full">
          {busy ? 'جار الدخول…' : 'تسجيل الدخول'}
        </Button>
      </form>
    </AuthLayout>
  )
}
