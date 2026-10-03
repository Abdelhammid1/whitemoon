import { useEffect, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { createProduct, listProducts, type Product } from '../../api/inventory'
import { ApiError } from '../../api/client'

export function ProductsPage() {
  const toast = useToast()
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [rows, setRows] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [form, setForm] = useState({ sku: '', name_ar: '', category: 'food', unit: 'piece' })
  const [busy, setBusy] = useState(false)

  async function load() {
    setLoading(true)
    try { setRows((await listProducts({ q: q || undefined, category: category || undefined })).items) }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [category]) // eslint-disable-line react-hooks/exhaustive-deps

  async function onCreate(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    try {
      await createProduct(form)
      toast.success('تم إنشاء المنتج.')
      setOpen(false)
      setForm({ sku: '', name_ar: '', category: 'food', unit: 'piece' })
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الإنشاء')
    } finally {
      setBusy(false)
    }
  }

  const chip = (active: boolean) =>
    `px-2 py-0.5 rounded-full font-mono-body text-small transition-colors ${active ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'}`

  return (
    <Wide>
      <div className="flex items-start justify-between">
        <PageTitle title="المنتجات والمخزون" subtitle="كتالوج موحّد مستقل عن المورد." />
        <Button variant="primary" onClick={() => setOpen(true)} iconRight="add">إضافة منتج</Button>
      </div>

      <div className="mt-space-xl flex flex-wrap items-end gap-space-md">
        <form onSubmit={(e) => { e.preventDefault(); void load() }} className="w-[320px]"><Field label="بحث (SKU / اسم)" value={q} onChange={(e) => setQ(e.target.value)} /></form>
        <div className="flex gap-space-xs">
          {['', 'food', 'clothing'].map((c) => (
            <button key={c || 'all'} className={chip(category === c)} onClick={() => setCategory(c)}>
              {c === '' ? 'الكل' : c === 'food' ? 'غذائية' : 'ملابس'}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-space-lg">
        {loading ? <Spinner /> : (
          <DataTable rows={rows} rowKey={(p) => p.id} empty="لا توجد منتجات." columns={[
            { header: 'SKU', cell: (p) => <Mono>{p.sku}</Mono> },
            { header: 'الاسم', cell: (p) => <span className="font-body text-body">{p.name_ar}</span> },
            { header: 'الفئة', cell: (p) => <Pill tone="neutral">{p.category === 'food' ? 'غذائية' : 'ملابس'}</Pill> },
            { header: 'الوحدة', cell: (p) => <span className="font-body text-body">{p.unit}</span> },
            { header: 'تتبع الصلاحية', cell: (p) => <span className="font-body text-body">{p.food_expiry_tracked ? 'نعم' : 'لا'}</span> },
            { header: 'الحالة', align: 'end', cell: (p) => <Pill tone={p.is_active ? 'signal' : 'neutral'}>{p.is_active ? 'نشط' : 'موقوف'}</Pill> },
          ]} />
        )}
      </div>

      <Modal open={open} onClose={() => setOpen(false)} title="إضافة منتج جديد" footer={
        <>
          <Button onClick={() => setOpen(false)}>إلغاء</Button>
          <Button variant="primary" onClick={onCreate} disabled={busy || !form.sku || !form.name_ar}>حفظ</Button>
        </>
      }>
        <form onSubmit={onCreate} className="flex flex-col gap-space-md">
          <Field label="SKU" dir="ltr" mono value={form.sku} onChange={(e) => setForm({ ...form, sku: e.target.value })} required />
          <Field label="الاسم بالعربية" value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} required />
          <div className="flex flex-col">
            <label className="font-small text-small text-secondary mb-1">الفئة</label>
            <select className="bg-transparent border-b border-surface-container-high py-2 font-body text-body focus:outline-none focus:border-primary" value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}>
              <option value="food">غذائية</option>
              <option value="clothing">ملابس</option>
            </select>
          </div>
          <Field label="الوحدة" value={form.unit} onChange={(e) => setForm({ ...form, unit: e.target.value })} />
        </form>
      </Modal>
    </Wide>
  )
}
