import { useCallback, useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Spinner, Pill, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { createAccount, listAccounts, updateAccount, type AccountRow } from '../../api/accounting'
import { ApiError } from '../../api/client'

const TYPE_AR: Record<string, string> = {
  asset: 'أصول',
  liability: 'التزامات',
  equity: 'حقوق ملكية',
  revenue: 'إيرادات',
  expense: 'مصروفات',
  contra: 'حساب مقابل',
}

/** Depth from the parent_code chain, to indent the tree. */
function depthOf(code: string, byCode: Map<string, AccountRow>): number {
  let d = 0
  let cur = byCode.get(code)?.parent_code ?? null
  while (cur && d < 8) {
    d += 1
    cur = byCode.get(cur)?.parent_code ?? null
  }
  return d
}

const EMPTY_CREATE = {
  code: '',
  name_ar: '',
  name_en: '',
  parent_code: '',
  is_postable: true,
  category: '',
  eta_code: '',
}

export function ChartOfAccountsPage() {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<AccountRow[]>([])
  const [busy, setBusy] = useState(false)

  const [modal, setModal] = useState<'create' | 'edit' | null>(null)
  const [cForm, setCForm] = useState(EMPTY_CREATE)
  const [editCode, setEditCode] = useState('')
  const [eForm, setEForm] = useState({ name_ar: '', name_en: '', is_postable: true, category: '', eta_code: '' })

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const r = await listAccounts()
      setRows(r.items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }, [])
  useEffect(() => {
    void load()
  }, [load])

  const byCode = new Map(rows.map((a) => [a.code, a]))

  function openCreate() {
    setCForm(EMPTY_CREATE)
    setModal('create')
  }
  function openEdit(a: AccountRow) {
    setEditCode(a.code)
    setEForm({
      name_ar: a.name_ar,
      name_en: a.name_en ?? '',
      is_postable: a.is_postable,
      category: a.category ?? '',
      eta_code: a.eta_code ?? '',
    })
    setModal('edit')
  }

  async function submitCreate() {
    setBusy(true)
    try {
      await createAccount({
        code: cForm.code.trim(),
        name_ar: cForm.name_ar.trim(),
        name_en: cForm.name_en.trim() || undefined,
        parent_code: cForm.parent_code,
        is_postable: cForm.is_postable,
        category: cForm.category.trim() || undefined,
        eta_code: cForm.eta_code.trim() || undefined,
      })
      toast.success('تم حفظ الحساب.')
      setModal(null)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally {
      setBusy(false)
    }
  }

  async function submitEdit() {
    setBusy(true)
    try {
      await updateAccount(editCode, {
        name_ar: eForm.name_ar.trim(),
        name_en: eForm.name_en.trim() || undefined,
        is_postable: eForm.is_postable,
        category: eForm.category.trim() || undefined,
        eta_code: eForm.eta_code.trim() || undefined,
      })
      toast.success('تم حفظ الحساب.')
      setModal(null)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally {
      setBusy(false)
    }
  }

  const createValid = cForm.code.trim() && cForm.name_ar.trim() && cForm.parent_code

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle title="دليل الحسابات" subtitle="شجرة الحسابات المعتمدة التي تُبنى عليها كل القيود." />
        <Button variant="primary" onClick={openCreate}>إضافة حساب</Button>
      </div>

      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          <DataTable
            rows={rows}
            rowKey={(a) => a.code}
            empty="لا توجد حسابات."
            columns={[
              {
                header: 'الكود',
                width: '90px',
                cell: (a) => <Mono>{a.code}</Mono>,
              },
              {
                header: 'اسم الحساب',
                cell: (a) => (
                  <span
                    className={a.is_postable ? 'font-body text-body text-on-surface' : 'font-medium text-body text-on-surface'}
                    style={{ paddingInlineStart: `${depthOf(a.code, byCode) * 16}px` }}
                  >
                    {a.name_ar}
                  </span>
                ),
              },
              {
                header: 'النوع',
                cell: (a) => <Pill tone="neutral">{TYPE_AR[a.type] ?? a.type}</Pill>,
              },
              {
                header: 'قابل للترحيل',
                align: 'center',
                cell: (a) =>
                  a.is_postable ? (
                    <Pill tone="signal">نعم</Pill>
                  ) : (
                    <span className="font-small text-small text-secondary">تجميعي</span>
                  ),
              },
              {
                header: 'ETA',
                align: 'end',
                cell: (a) => <Mono>{a.eta_code ?? '—'}</Mono>,
              },
              {
                header: '',
                align: 'end',
                cell: (a) => (
                  <button
                    className="font-small text-small text-primary hover:underline"
                    onClick={() => openEdit(a)}
                  >
                    تعديل
                  </button>
                ),
              },
            ]}
          />
        )}
      </div>

      {/* Create */}
      <Modal
        open={modal === 'create'}
        onClose={() => setModal(null)}
        title="إضافة حساب"
        footer={
          <>
            <Button onClick={() => setModal(null)}>إلغاء</Button>
            <Button variant="primary" disabled={busy || !createValid} onClick={() => void submitCreate()}>
              حفظ
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-space-md">
          <Field label="الكود" dir="ltr" mono value={cForm.code} onChange={(e) => setCForm({ ...cForm, code: e.target.value })} />
          <Field label="الاسم بالعربية" value={cForm.name_ar} onChange={(e) => setCForm({ ...cForm, name_ar: e.target.value })} />
          <Field label="الاسم بالإنجليزية (اختياري)" dir="ltr" value={cForm.name_en} onChange={(e) => setCForm({ ...cForm, name_en: e.target.value })} />
          <div className="w-full flex flex-col">
            <label className="font-small text-small text-secondary mb-1">الحساب الأب (يرث منه النوع)</label>
            <select
              dir="ltr"
              value={cForm.parent_code}
              onChange={(e) => setCForm({ ...cForm, parent_code: e.target.value })}
              className="w-full bg-transparent font-mono-body text-mono-body text-on-surface py-2 border-b border-surface-container-high focus:border-primary focus:border-b-2 focus:outline-none"
            >
              <option value="">— اختر الحساب الأب —</option>
              {rows.map((a) => (
                <option key={a.code} value={a.code}>
                  {a.code} — {a.name_ar}
                </option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-space-sm font-body text-body">
            <input type="checkbox" checked={cForm.is_postable} onChange={(e) => setCForm({ ...cForm, is_postable: e.target.checked })} /> قابل للترحيل
          </label>
          <Field label="التصنيف (اختياري)" value={cForm.category} onChange={(e) => setCForm({ ...cForm, category: e.target.value })} />
          <Field label="كود ETA (اختياري)" dir="ltr" mono value={cForm.eta_code} onChange={(e) => setCForm({ ...cForm, eta_code: e.target.value })} />
        </div>
      </Modal>

      {/* Edit */}
      <Modal
        open={modal === 'edit'}
        onClose={() => setModal(null)}
        title={`تعديل الحساب ${editCode}`}
        footer={
          <>
            <Button onClick={() => setModal(null)}>إلغاء</Button>
            <Button variant="primary" disabled={busy || !eForm.name_ar.trim()} onClick={() => void submitEdit()}>
              حفظ
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-space-md">
          <Field label="الاسم بالعربية" value={eForm.name_ar} onChange={(e) => setEForm({ ...eForm, name_ar: e.target.value })} />
          <Field label="الاسم بالإنجليزية (اختياري)" dir="ltr" value={eForm.name_en} onChange={(e) => setEForm({ ...eForm, name_en: e.target.value })} />
          <label className="flex items-center gap-space-sm font-body text-body">
            <input type="checkbox" checked={eForm.is_postable} onChange={(e) => setEForm({ ...eForm, is_postable: e.target.checked })} /> قابل للترحيل
          </label>
          <Field label="التصنيف (اختياري)" value={eForm.category} onChange={(e) => setEForm({ ...eForm, category: e.target.value })} />
          <Field label="كود ETA (اختياري)" dir="ltr" mono value={eForm.eta_code} onChange={(e) => setEForm({ ...eForm, eta_code: e.target.value })} />
        </div>
      </Modal>
    </Wide>
  )
}
