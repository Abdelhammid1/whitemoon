import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Spinner, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { listConversations, type Conversation } from '../../api/comm'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'

export function ChatPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isMod = user?.kind === 'admin' || user?.kind === 'staff'
  const [rows, setRows] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flagged, setFlagged] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setRows((await listConversations({ flagged: flagged || undefined })).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [flagged])
  useEffect(() => { void load() }, [load])

  return (
    <Wide>
      <PageTitle title="المحادثات" subtitle="قناة موجّهة عبر الشركة — هوية الطرف الآخر مخفية. كل الرسائل تمر عبر الخادم." />
      {isMod && (
        <label className="mt-space-md flex items-center gap-space-sm font-body text-body">
          <input type="checkbox" checked={flagged} onChange={(e) => setFlagged(e.target.checked)} /> المحظورة فقط
        </label>
      )}
      <div className="mt-space-lg">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : rows.length === 0 ? (
          <EmptyState title="لا توجد محادثات." />
        ) : (
          <DataTable rows={rows} rowKey={(c) => c.id} onRowClick={(c) => navigate(`/chat/${c.id}`)} columns={[
            { header: 'المحادثة', cell: (c) => <Mono>#{c.id}</Mono> },
            { header: 'الموضوع', cell: (c) => c.subject ?? (c.order_id ? `طلب #${c.order_id}` : '—') },
            {
              header: 'الطرف الآخر',
              cell: (c) => isMod
                ? <span className="font-mono-body text-mono-body">عميل {c.customer_id} ↔ مورد {c.supplier_id}</span>
                : (c.counterpart_role === 'supplier' ? 'المورد' : 'العميل'),
            },
            { header: 'الحالة', align: 'center', cell: (c) => <Pill tone={c.flagged ? 'error' : c.status === 'open' ? 'signal' : 'neutral'}>{c.flagged ? 'محظورة' : c.status === 'open' ? 'مفتوحة' : 'مغلقة'}</Pill> },
          ]} />
        )}
      </div>
    </Wide>
  )
}
