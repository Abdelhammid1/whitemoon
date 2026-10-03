import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Card, CardHeader } from '../../components/Card'
import { Input } from '../../components/Input'
import { Button } from '../../components/Button'
import { registerSupplier } from '../../api/auth'
import { ApiError } from '../../api/client'

export function RegisterSupplierPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = useState<string>('')
  const [email, setEmail] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const [legalName, setLegalName] = useState<string>('')
  const [crNo, setCrNo] = useState<string>('')
  const [taxNo, setTaxNo] = useState<string>('')
  const [nationalId, setNationalId] = useState<string>('')
  const [busy, setBusy] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      const resp = await registerSupplier({
        phone: phone || undefined,
        email: email || undefined,
        password,
        legal_name: legalName,
        commercial_register_no: crNo,
        tax_card_no: taxNo,
        national_id: nationalId,
      })
      navigate(
        `/otp?user_id=${resp.user_id}&channel=${encodeURIComponent(resp.otp.channel)}&debug=${encodeURIComponent(resp.otp.debug_code ?? '')}&supplier=1`,
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
          title="تسجيل مورد"
          subtitle="لن يُفعّل الحساب إلا بعد اعتماد الإدارة لبياناتك الرسمية."
        />
        <form onSubmit={onSubmit} className="flex flex-col gap-3">
          <Input
            label="الاسم القانوني"
            value={legalName}
            onChange={(e) => setLegalName(e.target.value)}
            required
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="رقم السجل التجاري"
              value={crNo}
              dir="ltr"
              onChange={(e) => setCrNo(e.target.value)}
              required
            />
            <Input
              label="رقم البطاقة الضريبية"
              value={taxNo}
              dir="ltr"
              onChange={(e) => setTaxNo(e.target.value)}
              required
            />
          </div>
          <Input
            label="الرقم القومي"
            value={nationalId}
            dir="ltr"
            onChange={(e) => setNationalId(e.target.value)}
            required
          />
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <Input
              label="رقم الهاتف"
              type="tel"
              dir="ltr"
              placeholder="+2010XXXXXXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
            <Input
              label="البريد الإلكتروني"
              type="email"
              dir="ltr"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <Input
            label="كلمة المرور"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
          />
          {error && (
            <div className="rounded-md border border-warm-mist bg-soft-paper px-3 py-2 text-body-sm text-ink">
              {error}
            </div>
          )}
          <Button variant="filled" type="submit" disabled={busy}>
            {busy ? 'جار الإنشاء…' : 'إنشاء حساب مورد'}
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
