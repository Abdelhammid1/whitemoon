import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Spinner, Pill, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listAccounts, type AccountRow } from '../../api/accounting'
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

export function ChartOfAccountsPage() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<AccountRow[]>([])

  useEffect(() => {
    listAccounts()
      .then((r) => setRows(r.items))
      .catch((err) => setError(err instanceof ApiError ? err.message : 'تعذّر التحميل'))
      .finally(() => setLoading(false))
  }, [])

  const byCode = new Map(rows.map((a) => [a.code, a]))

  return (
    <Wide>
      <PageTitle title="دليل الحسابات" subtitle="شجرة الحسابات المعتمدة التي تُبنى عليها كل القيود." />
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
            ]}
          />
        )}
      </div>
    </Wide>
  )
}
