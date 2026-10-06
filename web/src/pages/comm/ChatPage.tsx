import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Field, Card, Spinner, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Icon } from '../../components/Icon'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { listConversations, startConversation, type Conversation } from '../../api/comm'
import { useAuth } from '../../auth/AuthContext'
import { ApiError } from '../../api/client'
import { PageHelp } from '../../components/PageHelp'

export function ChatPage() {
  const navigate = useNavigate()
  const toast = useToast()
  const { user } = useAuth()
  // Moderation (viewing both parties, the flagged filter, opening a
  // conversation) is the comm.moderate permission — granted to admin only,
  // not staff. Gating on kind keeps the UI in step with the backend decorator.
  const isMod = user?.kind === 'admin'
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
      <div className="flex flex-wrap items-start justify-between gap-space-md">
        <PageTitle title="المحادثات" subtitle="قناة موجّهة عبر الشركة — هوية الطرف الآخر مخفية. كل الرسائل تمر عبر الخادم." />
        {isMod && (
          <Button variant="primary" onClick={() => setNewOpen(true)} iconRight="add">
            محادثة جديدة
          </Button>
        )}
      </div>
      <PageHelp pageKey="chat" />

      {isMod && (
        <label className="mt-space-lg inline-flex items-center gap-space-sm cursor-pointer select-none rounded-lg border border-surface-container-high bg-surface-container-lowest px-space-md py-space-sm font-body-medium text-body-medium text-on-surface shadow-card-sm transition-colors hover:bg-surface-container-low">
          <input
            type="checkbox"
            checked={flagged}
            onChange={(e) => setFlagged(e.target.checked)}
            className="h-4 w-4 accent-primary"
          />
          <Icon name="flag" size={16} className="text-danger" />
          المحظورة فقط
        </label>
      )}

      <div className="mt-space-lg">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : rows.length === 0 ? (
          <Card>
            <EmptyState title="لا توجد محادثات." description="لم تُفتح أي قناة وساطة بعد." />
          </Card>
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable rows={rows} rowKey={(c) => c.id} onRowClick={(c) => navigate(`/chat/${c.id}`)} columns={[
              { header: 'المحادثة', cell: (c) => <Mono>#{c.id}</Mono> },
              { header: 'الموضوع', cell: (c) => c.subject ?? (c.order_id ? `طلب #${c.order_id}` : '—') },
              {
                header: 'الطرف الآخر',
                cell: (c) => isMod
                  ? <span className="font-mono-body text-mono-body" dir="ltr">عميل {c.customer_id} ↔ مورد {c.supplier_id}</span>
                  : (
                      <span className="inline-flex items-center gap-1.5 font-body-medium text-body-medium text-on-surface">
                        <Icon name="shield_person" size={16} className="text-secondary" />
                        {c.counterpart_role === 'supplier' ? 'المورد' : 'العميل'}
                      </span>
                    ),
              },
              { header: 'الحالة', align: 'center', cell: (c) => <Pill tone={c.flagged ? 'error' : c.status === 'open' ? 'signal' : 'neutral'}>{c.flagged ? 'محظورة' : c.status === 'open' ? 'مفتوحة' : 'مغلقة'}</Pill> },
            ]} />
          </Card>
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
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-space-md">
            <Field label="رقم العميل" dir="ltr" mono inputMode="numeric" value={nc.customer_id} onChange={(e) => setNc({ ...nc, customer_id: e.target.value })} />
            <Field label="رقم المورد" dir="ltr" mono inputMode="numeric" value={nc.supplier_id} onChange={(e) => setNc({ ...nc, supplier_id: e.target.value })} />
          </div>
          <Field label="رقم الطلب (اختياري)" dir="ltr" mono inputMode="numeric" value={nc.order_id} onChange={(e) => setNc({ ...nc, order_id: e.target.value })} />
          <Field label="الموضوع (اختياري)" value={nc.subject} onChange={(e) => setNc({ ...nc, subject: e.target.value })} />
        </div>
      </Modal>
    </Wide>
  )
}
