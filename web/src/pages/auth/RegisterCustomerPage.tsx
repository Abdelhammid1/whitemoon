import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Button, Field, InlineError } from '../../components/ui'
import { registerCustomer } from '../../api/auth'
import { ApiError } from '../../api/client'

export function RegisterCustomerPage() {
  const navigate = useNavigate()
  const [displayName, setDisplayName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
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
    <AuthLayout
      title="حساب عميل جديد"
      subtitle="يُفعَّل حسابك فور التحقق من رقم الهاتف."
      footerLinks={<Link to="/login" className="hover:text-on-surface">لديك حساب؟ تسجيل الدخول</Link>}
    >
      <form onSubmit={onSubmit} className="w-full flex flex-col gap-5">
        <Field label="الاسم الظاهر" value={displayName} onChange={(e) => setDisplayName(e.target.value)} required maxLength={200} />
        <Field label="رقم الهاتف" dir="ltr" mono type="tel" placeholder="+20 100 000 0000" value={phone} onChange={(e) => setPhone(e.target.value)} hint="اكتب الهاتف أو البريد — الأفضل الاثنين." />
        <Field label="البريد الإلكتروني (اختياري)" dir="ltr" type="email" placeholder="you@domain.com.eg" value={email} onChange={(e) => setEmail(e.target.value)} />
        <Field label="كلمة المرور" type="password" mono placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        {error && <InlineError message={error} />}
        <Button variant="primary" type="submit" disabled={busy} className="w-full">
          {busy ? 'جار الإنشاء…' : 'إنشاء الحساب'}
        </Button>
      </form>
    </AuthLayout>
  )
}
