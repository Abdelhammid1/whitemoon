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
        <fieldset className="flex flex-col gap-space-md">
          <legend className="font-small-medium text-small-medium text-secondary mb-space-sm">بيانات الدخول</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <Field label="رقم الهاتف" dir="ltr" mono type="tel" placeholder="+20 100 000 0000" value={phone} onChange={(e) => setPhone(e.target.value)} />
            <Field label="البريد الإلكتروني" dir="ltr" type="email" placeholder="enterprise@domain.com.eg" value={email} onChange={(e) => setEmail(e.target.value)} />
            <div className="md:col-span-2">
              <Field label="كلمة المرور" type="password" mono placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
            </div>
          </div>
        </fieldset>

        <fieldset className="flex flex-col gap-space-md">
          <legend className="font-small-medium text-small-medium text-secondary mb-space-sm">البيانات الرسمية</legend>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-space-md">
            <div className="md:col-span-2">
              <Field label="الاسم القانوني" value={legalName} onChange={(e) => setLegalName(e.target.value)} required />
            </div>
            <Field label="رقم السجل التجاري" dir="ltr" mono value={crNo} onChange={(e) => setCrNo(e.target.value)} required />
            <Field label="رقم البطاقة الضريبية" dir="ltr" mono value={taxNo} onChange={(e) => setTaxNo(e.target.value)} required />
            <div className="md:col-span-2">
              <Field label="الرقم القومي" dir="ltr" mono value={nationalId} onChange={(e) => setNationalId(e.target.value)} required />
            </div>
          </div>
        </fieldset>

        <div className="flex items-start gap-space-sm rounded-xl bg-surface-container-low p-space-md font-small text-small text-secondary">
          <span className="w-8 h-8 rounded-xl bg-gold-weak flex items-center justify-center shrink-0">
            <Icon name="verified_user" size={18} className="text-gold" />
          </span>
          <span className="leading-relaxed pt-space-xs">لن يُفعَّل الحساب إلا بعد اعتماد الإدارة للمستندات الرسمية.</span>
        </div>

        {error && <InlineError message={error} />}
        <Button variant="primary" type="submit" disabled={busy} className="w-full">
          {busy ? 'جار الإنشاء…' : 'إنشاء حساب مورد'}
        </Button>
      </form>
    </AuthLayout>
  )
}
