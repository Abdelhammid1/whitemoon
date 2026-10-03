import { useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Spinner, EmptyState } from '../../components/ui'
import { listOrPending, EndpointPending } from '../../api/pending'

interface AccountRow {
  code: string
  name_ar: string
  type: string
  is_postable: boolean
}

export function ChartOfAccountsPage() {
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(false)
  const [, setRows] = useState<AccountRow[]>([])

  useEffect(() => {
    listOrPending<AccountRow>('/accounting/accounts')
      .then(setRows)
      .catch((err) => { if (err instanceof EndpointPending) setPending(true) })
      .finally(() => setLoading(false))
  }, [])

  return (
    <Wide>
      <PageTitle title="دليل الحسابات" subtitle="شجرة الحسابات المعتمدة التي تُبنى عليها كل القيود." />
      <div className="mt-space-xl">
        {loading ? (
          <Spinner />
        ) : pending ? (
          <EmptyState
            title="عرض دليل الحسابات قيد الإنشاء"
            description="شجرة الحسابات مُعتمدة ومُهيّأة في قاعدة البيانات؛ واجهة استعراضها لم تُفعَّل بعد على الخادم."
          />
        ) : (
          <EmptyState title="لا توجد حسابات." />
        )}
      </div>
    </Wide>
  )
}
