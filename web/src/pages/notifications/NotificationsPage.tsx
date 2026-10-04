import { useCallback, useEffect, useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Pill, Spinner, EmptyState, InlineError } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { listNotifications, markAllRead, markRead, type Notification } from '../../api/notifications'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const CHANNEL_AR: Record<string, string> = {
  in_app: 'داخل التطبيق', sms: 'SMS', whatsapp: 'واتساب', email: 'بريد',
}

export function NotificationsPage() {
  const toast = useToast()
  const [rows, setRows] = useState<Notification[]>([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { const r = await listNotifications(); setRows(r.items); setUnread(r.unread) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function readOne(id: number) {
    try { await markRead(id); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل') }
  }
  async function readAll() {
    try { const r = await markAllRead(); toast.success(`${r.marked} إشعار`); await load() }
    catch (err) { toast.error(err instanceof ApiError ? err.message : 'فشل') }
  }

  return (
    <Narrow>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="مركز الإشعارات" subtitle={`غير مقروء: ${unread}`} />
        {unread > 0 && <Button onClick={readAll}>تعليم الكل كمقروء</Button>}
      </div>
      <div className="mt-space-xl">
        {loading ? <Spinner /> : error ? <InlineError message={error} /> : rows.length === 0 ? (
          <EmptyState title="لا توجد إشعارات." />
        ) : (
          <div className="flex flex-col">
            {rows.map((n) => (
              <button key={n.id} onClick={() => !n.is_read && readOne(n.id)}
                className={`text-start flex flex-col gap-space-xs py-space-md border-b border-surface-container-high ${n.is_read ? 'opacity-60' : 'hover:bg-surface'}`}>
                <div className="flex items-center justify-between gap-space-sm">
                  <span className="font-body-medium text-body-medium text-on-surface">{n.title}</span>
                  <div className="flex items-center gap-space-xs">
                    <Pill tone="neutral">{CHANNEL_AR[n.channel] ?? n.channel}</Pill>
                    {!n.is_read && <span className="w-2 h-2 rounded-full bg-[#0F6B3E]" />}
                  </div>
                </div>
                {n.body && <span className="font-body text-body text-secondary">{n.body}</span>}
                <span className="font-mono-body text-mono-body text-secondary">{formatDate(n.created_at)}</span>
              </button>
            ))}
          </div>
        )}
      </div>
    </Narrow>
  )
}
