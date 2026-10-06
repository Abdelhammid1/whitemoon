import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, Card } from '../../components/ui'
import { Modal } from '../../components/Overlay'
import { Icon } from '../../components/Icon'
import { useToast } from '../../components/Toast'
import {
  listCategoriesManage,
  createCategory,
  updateCategory,
  deleteCategory,
  type ManagedCategory,
} from '../../api/inventory'
import { ApiError } from '../../api/client'

const EMPTY = { code: '', name_ar: '', name_en: '', icon: '', parent_code: '' }

export function CategoriesPage() {
  const toast = useToast()
  const [cats, setCats] = useState<ManagedCategory[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<ManagedCategory | null>(null)
  const [form, setForm] = useState({ ...EMPTY })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    try {
      setCats((await listCategoriesManage()).items)
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => { void load() }, [])

  const tops = useMemo(
    () => cats.filter((c) => !c.parent_code).sort((a, b) => a.sort_order - b.sort_order),
    [cats],
  )
  const childrenOf = (code: string) =>
    cats.filter((c) => c.parent_code === code).sort((a, b) => a.sort_order - b.sort_order)

  function openNew() { setEditing(null); setForm({ ...EMPTY }); setErr(null); setOpen(true) }
  function openEdit(c: ManagedCategory) {
    setEditing(c)
    setForm({ code: c.code, name_ar: c.name_ar, name_en: c.name_en ?? '', icon: c.icon ?? '', parent_code: c.parent_code ?? '' })
    setErr(null); setOpen(true)
  }

  async function submit(e: FormEvent) {
    e.preventDefault()
    if (!form.name_ar.trim()) { setErr('الاسم بالعربي مطلوب'); return }
    setBusy(true); setErr(null)
    try {
      if (editing) {
        await updateCategory(editing.code, {
          name_ar: form.name_ar, name_en: form.name_en, icon: form.icon, parent_code: form.parent_code,
        })
        toast.success('تم التحديث.')
      } else {
        await createCategory({
          name_ar: form.name_ar, code: form.code || undefined, name_en: form.name_en || undefined,
          icon: form.icon || undefined, parent_code: form.parent_code || undefined,
        })
        toast.success('تمت إضافة الفئة.')
      }
      setOpen(false); await load()
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : 'تعذّر الحفظ')
    } finally {
      setBusy(false)
    }
  }

  async function toggleActive(c: ManagedCategory) {
    try {
      await updateCategory(c.code, { is_active: !c.is_active })
      await load()
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : 'تعذّر التغيير')
    }
  }

  async function remove(c: ManagedCategory) {
    try {
      await deleteCategory(c.code)
      toast.success('تم الحذف.')
      await load()
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : 'تعذّر الحذف')
    }
  }

  async function move(c: ManagedCategory, dir: -1 | 1) {
    const siblings = c.parent_code ? childrenOf(c.parent_code) : tops
    const i = siblings.findIndex((s) => s.code === c.code)
    const j = i + dir
    if (j < 0 || j >= siblings.length) return
    const other = siblings[j]
    if (!other) return
    try {
      await updateCategory(c.code, { sort_order: other.sort_order })
      await updateCategory(other.code, { sort_order: c.sort_order })
      await load()
    } catch (e) {
      toast.error(e instanceof ApiError ? e.message : 'تعذّر الترتيب')
    }
  }

  function Row({ c, child }: { c: ManagedCategory; child?: boolean }) {
    return (
      <div className={`flex items-center gap-space-md py-space-sm ${child ? 'ps-space-xl' : ''}`}>
        <span className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 ${c.is_active ? 'bg-brand-weak text-primary' : 'bg-surface-container text-outline'}`}>
          <Icon name={c.icon || 'category'} size={18} />
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-space-sm">
            <span className="font-body-medium text-body-medium text-on-surface truncate">{c.name_ar}</span>
            {!c.is_active && <Pill tone="neutral">موقوفة</Pill>}
          </div>
          <span className="font-mono-body text-small text-outline" dir="ltr">{c.code} · {c.product_count} منتج</span>
        </div>
        <div className="flex items-center gap-space-xs shrink-0">
          <button onClick={() => move(c, -1)} className="w-8 h-8 rounded-lg flex items-center justify-center text-secondary hover:bg-surface-container-low" aria-label="أعلى"><Icon name="keyboard_arrow_up" size={18} /></button>
          <button onClick={() => move(c, 1)} className="w-8 h-8 rounded-lg flex items-center justify-center text-secondary hover:bg-surface-container-low" aria-label="أسفل"><Icon name="keyboard_arrow_down" size={18} /></button>
          <button onClick={() => toggleActive(c)} className="text-small-medium text-small-medium px-space-sm py-1 rounded-lg text-secondary hover:bg-surface-container-low">{c.is_active ? 'إيقاف' : 'تفعيل'}</button>
          <button onClick={() => openEdit(c)} className="text-small-medium text-small-medium px-space-sm py-1 rounded-lg text-primary hover:bg-surface-container-low">تعديل</button>
          <button onClick={() => remove(c)} className="text-small-medium text-small-medium px-space-sm py-1 rounded-lg text-danger hover:bg-danger-weak">حذف</button>
        </div>
      </div>
    )
  }

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle title="الفئات" subtitle="شجرة الفئات الرئيسية والفرعية — يديرها الأدمن وتظهر فورًا في الكتالوج ونموذج المنتج." />
        <Button variant="primary" onClick={openNew} iconRight="add">فئة جديدة</Button>
      </div>

      <div className="mt-space-xl">
        {loading ? <Spinner /> : tops.length === 0 ? (
          <EmptyState title="لا توجد فئات." description="اضغط «فئة جديدة» لإضافة أول فئة." action={<Button variant="primary" onClick={openNew}>فئة جديدة</Button>} />
        ) : (
          <div className="flex flex-col gap-space-md">
            {tops.map((t) => {
              const kids = childrenOf(t.code)
              return (
                <Card key={t.code} padded={false} className="px-space-lg py-space-xs">
                  <Row c={t} />
                  {kids.length > 0 && (
                    <div className="border-t border-surface-container-high divide-y divide-surface-container-high">
                      {kids.map((k) => <Row key={k.code} c={k} child />)}
                    </div>
                  )}
                </Card>
              )
            })}
          </div>
        )}
      </div>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title={editing ? 'تعديل الفئة' : 'فئة جديدة'}
        footer={
          <>
            <Button onClick={() => setOpen(false)}>إلغاء</Button>
            <Button variant="primary" disabled={busy} onClick={(e) => void submit(e as unknown as FormEvent)}>
              {busy ? 'جارٍ…' : editing ? 'حفظ' : 'إضافة'}
            </Button>
          </>
        }
      >
        <form onSubmit={submit} className="flex flex-col gap-space-md">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="الاسم بالعربي" value={form.name_ar} onChange={(e) => setForm({ ...form, name_ar: e.target.value })} required />
            <Field label="الاسم بالإنجليزي (اختياري)" dir="ltr" value={form.name_en} onChange={(e) => setForm({ ...form, name_en: e.target.value })} />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            {!editing && (
              <Field label="الكود (اختياري)" dir="ltr" mono value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} hint="يُشتق من الاسم إن تُرك فارغًا" />
            )}
            <div className="flex flex-col">
              <label className="font-small text-small text-secondary mb-1">الفئة الأم (اختياري)</label>
              <select
                className="w-full bg-transparent font-body text-body text-on-surface py-2 border-b border-surface-container-high focus:border-primary focus:border-b-2 focus:outline-none"
                value={form.parent_code}
                onChange={(e) => setForm({ ...form, parent_code: e.target.value })}
              >
                <option value="">— فئة رئيسية —</option>
                {tops.filter((t) => t.code !== editing?.code).map((t) => (
                  <option key={t.code} value={t.code}>{t.name_ar}</option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex items-end gap-space-md">
            <div className="flex-1"><Field label="الأيقونة (اسم Material Symbol)" dir="ltr" value={form.icon} onChange={(e) => setForm({ ...form, icon: e.target.value })} hint="مثال: restaurant، devices، spa" /></div>
            <span className="w-11 h-11 rounded-xl bg-brand-weak text-primary flex items-center justify-center shrink-0"><Icon name={form.icon || 'category'} size={20} /></span>
          </div>
          {err && <p className="font-small text-small text-danger">{err}</p>}
        </form>
      </Modal>
    </Wide>
  )
}
