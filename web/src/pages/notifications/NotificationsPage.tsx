import { useCallback, useEffect, useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, InlineError } from '../../components/ui'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { listNotifications, markAllRead, markRead, sendNotification, type Notification } from '../../api/notifications'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const CHANNEL_AR: Record<string, string> = {
  in_app: 'داخل التطبيق', sms: 'SMS', whatsapp: 'واتساب', email: 'بريد',
}
const CHANNELS = ['in_app', 'sms', 'whatsapp', 'email'] as const

export function NotificationsPage() {
  const toast = useToast()
  const { user } = useAuth()
  const isAdmin = user?.kind === 'admin'
  const [rows, setRows] = useState<Notification[]>([])
  const [unread, setUnread] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [sendOpen, setSendOpen] = useState(false)
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ user_id: '', title: '', body: '', channel: 'in_app' as string })

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

  async function send() {
    setBusy(true)
    try {
      await sendNotification({
        user_id: Number(form.user_id),
        title: form.title.trim(),
        body: form.body.trim() || undefined,
        type: 'system',
        channel: form.channel,
      })
      toast.success('تم إرسال الإشعار.')
      setSendOpen(false)
      setForm({ user_id: '', title: '', body: '', channel: 'in_app' })
      if (Number(form.user_id) === user?.id) await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الإرسال')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Narrow>
      <div className="flex items-center justify-between gap-space-md">
        <PageTitle title="مركز الإشعارات" subtitle={`غير مقروء: ${unread}`} />
        <div className="flex items-center gap-space-sm">
          {isAdmin && <Button onClick={() => setSendOpen(true)}>إرسال إشعار</Button>}
          {unread > 0 && <Button onClick={readAll}>تعليم الكل كمقروء</Button>}
        </div>
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

      {isAdmin && (
        <Modal
          open={sendOpen}
          onClose={() => setSendOpen(false)}
          title="إرسال إشعار"
          footer={
            <>
              <Button onClick={() => setSendOpen(false)}>إلغاء</Button>
              <Button variant="primary" disabled={busy || !form.user_id || !form.title.trim()} onClick={() => void send()}>
                إرسال
              </Button>
            </>
          }
        >
          <div className="flex flex-col gap-space-md">
            <Field label="رقم المستخدم" dir="ltr" mono inputMode="numeric" value={form.user_id}
              onChange={(e) => setForm({ ...form, user_id: e.target.value })} />
            <Field label="العنوان" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <Field label="النص (اختياري)" value={form.body} onChange={(e) => setForm({ ...form, body: e.target.value })} />
            <div className="flex flex-col gap-space-xs">
              <span className="font-small text-small text-secondary">القناة</span>
              <div className="flex flex-wrap gap-space-xs">
                {CHANNELS.map((c) => (
                  <button key={c} type="button" onClick={() => setForm({ ...form, channel: c })}
                    className={`px-3 py-1 rounded-full font-small ${form.channel === c ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'}`}>
                    {CHANNEL_AR[c]}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </Modal>
      )}
    </Narrow>
  )
}
