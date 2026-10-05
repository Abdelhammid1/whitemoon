import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Field, Spinner, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { listConversations, startConversation, type Conversation } from '../../api/comm'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'

export function ChatPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  const isMod = user?.kind === 'admin' || user?.kind === 'staff'
  const [rows, setRows] = useState<Conversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [flagged, setFlagged] = useState(false)
  // Moderator-opened conversation: requires both party IDs, which only
  // admins/staff can see (identities stay hidden from customers/suppliers).
  const [newOpen, setNewOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [nc, setNc] = useState({ customer_id: '', supplier_id: '', order_id: '', subject: '' })

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setRows((await listConversations({ flagged: flagged || undefined })).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [flagged])
  useEffect(() => { void load() }, [load])

  const canStart = !busy && nc.customer_id.trim() !== '' && nc.supplier_id.trim() !== ''

  async function startNew() {
    setBusy(true)
    try {
      const conv = await startConversation({
        customer_id: Number(nc.customer_id),
        supplier_id: Number(nc.supplier_id),
        order_id: nc.order_id.trim() ? Number(nc.order_id) : undefined,
        subject: nc.subject.trim() || undefined,
      })
      toast.success('تم فتح المحادثة.')
      setNewOpen(false)
      setNc({ customer_id: '', supplier_id: '', order_id: '', subject: '' })
      navigate(`/chat/${conv.id}`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر فتح المحادثة')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle title="المحادثات" subtitle="قناة موجّهة عبر الشركة — هوية الطرف الآخر مخفية. كل الرسائل تمر عبر الخادم." />
        {isMod && <Button variant="primary" onClick={() => setNewOpen(true)}>محادثة جديدة</Button>}
      </div>
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

      <Modal
        open={newOpen}
        onClose={() => setNewOpen(false)}
        title="محادثة جديدة"
        footer={
          <>
            <Button onClick={() => setNewOpen(false)}>إلغاء</Button>
            <Button variant="primary" disabled={!canStart} onClick={() => void startNew()}>فتح</Button>
          </>
        }
      >
        <div className="flex flex-col gap-space-md">
          <div className="flex gap-space-md">
            <div className="flex-1"><Field label="رقم العميل" dir="ltr" mono inputMode="numeric" value={nc.customer_id} onChange={(e) => setNc({ ...nc, customer_id: e.target.value })} /></div>
            <div className="flex-1"><Field label="رقم المورد" dir="ltr" mono inputMode="numeric" value={nc.supplier_id} onChange={(e) => setNc({ ...nc, supplier_id: e.target.value })} /></div>
          </div>
          <Field label="رقم الطلب (اختياري)" dir="ltr" mono inputMode="numeric" value={nc.order_id} onChange={(e) => setNc({ ...nc, order_id: e.target.value })} />
          <Field label="الموضوع (اختياري)" value={nc.subject} onChange={(e) => setNc({ ...nc, subject: e.target.value })} />
        </div>
      </Modal>
    </Wide>
  )
}
