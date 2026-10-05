import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Pill, Button, Card, Spinner, EmptyState, InlineError } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Icon } from '../../components/Icon'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { listFlagged, listMessages, type FlaggedConversation, type Message } from '../../api/comm'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const ROLE_AR: Record<string, string> = {
  customer: 'العميل', supplier: 'المورد', admin: 'الإدارة', moderator: 'الإدارة', staff: 'الإدارة',
}
const REASON_AR: Record<string, string> = {
  phone_number: 'محاولة تبادل رقم هاتف',
  email: 'محاولة تبادل بريد إلكتروني',
}
function reasonLabel(r?: string): string {
  return (r && REASON_AR[r]) || 'محاولة تبادل بيانات اتصال'
}

export function ModerationPage() {
  const toast = useToast()
  const [rows, setRows] = useState<FlaggedConversation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [active, setActive] = useState<FlaggedConversation | null>(null)
  const [blocked, setBlocked] = useState<Message[]>([])
  const [modalLoading, setModalLoading] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { setRows((await listFlagged()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function open(conv: FlaggedConversation) {
    setActive(conv); setBlocked([]); setModalLoading(true)
    try {
      const { items } = await listMessages(conv.id)
      setBlocked(items.filter((m) => m.status === 'blocked'))
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تحميل الرسائل')
    } finally {
      setModalLoading(false)
    }
  }

  return (
    <Wide>
      <PageTitle
        title="مراقبة المحادثات"
        subtitle="المحادثات التي تحتوي رسائل محظورة. كل الرسائل تمر عبر الشركة وتخضع للرقابة الآلية."
      />

      <div className="mt-space-lg">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : rows.length === 0 ? (
          <Card>
            <EmptyState title="لا توجد محادثات محظورة." description="لم يرصد النظام أي محاولة تبادل بيانات اتصال." />
          </Card>
        ) : (
          <Card padded={false} className="overflow-hidden">
            <DataTable
              rows={rows}
              rowKey={(c) => c.id}
              onRowClick={(c) => void open(c)}
              columns={[
                {
                  header: 'المحادثة',
                  cell: (c) => (
                    <div className="flex flex-col">
                      <Mono>#{c.id}</Mono>
                      {c.subject && <span className="font-small text-small text-secondary">{c.subject}</span>}
                    </div>
                  ),
                },
                { header: 'الطلب', cell: (c) => (c.order_id ? <Mono>#{c.order_id}</Mono> : '—') },
                {
                  header: 'الطرفان',
                  cell: (c) => (
                    <span className="font-mono-body text-mono-body" dir="ltr">
                      عميل #{c.customer_id} ↔ مورد #{c.supplier_id}
                    </span>
                  ),
                },
                {
                  header: 'الرسائل المحجوبة',
                  align: 'center',
                  cell: (c) => <Pill tone="error">{c.blocked_count}</Pill>,
                },
                {
                  header: 'الحالة',
                  align: 'center',
                  cell: (c) => (
                    <Pill tone={c.status === 'open' ? 'signal' : 'neutral'}>
                      {c.status === 'open' ? 'مفتوحة' : 'مغلقة'}
                    </Pill>
                  ),
                },
              ]}
            />
          </Card>
        )}
      </div>

      <Modal
        open={active !== null}
        onClose={() => setActive(null)}
        title={active ? `الرسائل المحجوبة — محادثة #${active.id}` : 'الرسائل المحجوبة'}
        footer={
          active ? (
            <>
              <Button onClick={() => setActive(null)}>إغلاق</Button>
              <Link to={`/chat/${active.id}`}>
                <Button variant="primary">فتح المحادثة كاملة ↗</Button>
              </Link>
            </>
          ) : undefined
        }
      >
        {modalLoading ? (
          <Spinner />
        ) : blocked.length === 0 ? (
          <EmptyState title="لا توجد رسائل محجوبة في هذه المحادثة." />
        ) : (
          <div className="flex flex-col gap-space-md">
            {blocked.map((m) => (
              <div key={m.id} className="flex flex-col gap-space-sm border-b border-surface-container-high pb-space-md last:border-b-0 last:pb-0">
                <div className="flex items-center justify-between gap-space-sm">
                  <span className="font-body-medium text-body-medium text-on-surface">
                    {ROLE_AR[m.sender_role] ?? m.sender_role}
                    {m.sender_id != null && (
                      <span className="font-mono-body text-mono-body text-secondary"> · #{m.sender_id}</span>
                    )}
                  </span>
                  <span className="font-mono-body text-mono-body text-secondary" dir="ltr">
                    {formatDate(m.created_at)}
                  </span>
                </div>
                {m.body && <p className="font-body text-body text-on-surface">{m.body}</p>}
                <div className="flex items-center gap-space-sm rounded-lg border border-danger/25 bg-danger-weak px-space-sm py-space-xs">
                  <Icon name="block" size={16} className="text-danger shrink-0" />
                  <span className="font-small-medium text-small-medium text-danger">
                    حُجبت: {reasonLabel(m.block_reason)}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>
    </Wide>
  )
}
