import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { AuthLayout } from '../../layouts/AuthLayout'
import { Button, Field, InlineError } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { registerSupplier } from '../../api/auth'
import { ApiError } from '../../api/client'

export function RegisterSupplierPage() {
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [legalName, setLegalName] = useState('')
  const [crNo, setCrNo] = useState('')
  const [taxNo, setTaxNo] = useState('')
  const [nationalId, setNationalId] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(e: FormEvent) {
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
    <AuthLayout
      title="تسجيل مورد تجاري"
      footerLinks={<Link to="/login" className="hover:text-on-surface">لديك حساب؟ تسجيل الدخول</Link>}
    >
      <form onSubmit={onSubmit} className="w-full flex flex-col gap-space-xl">
        <div className="flex flex-col gap-5">
          <p className="font-small-medium text-small-medium text-secondary">بيانات الدخول</p>
          <Field label="رقم الهاتف" dir="ltr" mono type="tel" placeholder="+20 100 000 0000" value={phone} onChange={(e) => setPhone(e.target.value)} />
          <Field label="البريد الإلكتروني" dir="ltr" type="email" placeholder="enterprise@domain.com.eg" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Field label="كلمة المرور" type="password" mono placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
        </div>

        <div className="flex flex-col gap-5">
          <p className="font-small-medium text-small-medium text-secondary">البيانات الرسمية</p>
          <Field label="الاسم القانوني" value={legalName} onChange={(e) => setLegalName(e.target.value)} required />
          <Field label="رقم السجل التجاري" dir="ltr" mono value={crNo} onChange={(e) => setCrNo(e.target.value)} required />
          <Field label="رقم البطاقة الضريبية" dir="ltr" mono value={taxNo} onChange={(e) => setTaxNo(e.target.value)} required />
          <Field label="الرقم القومي" dir="ltr" mono value={nationalId} onChange={(e) => setNationalId(e.target.value)} required />
        </div>

        <div className="flex items-start gap-space-sm font-small text-small text-secondary">
          <Icon name="verified_user" size={18} className="text-secondary shrink-0" />
          <span>لن يُفعَّل الحساب إلا بعد اعتماد الإدارة للمستندات الرسمية.</span>
        </div>

        {error && <InlineError message={error} />}
        <Button variant="primary" type="submit" disabled={busy} className="w-full">
          {busy ? 'جار الإنشاء…' : 'إنشاء حساب مورد'}
        </Button>
      </form>
    </AuthLayout>
  )
}
