import { useCallback, useEffect, useState } from 'react'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Spinner, EmptyState, InlineError } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { Modal } from '../../components/Overlay'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import { listChannels, listNotifications, markAllRead, markRead, sendNotification, type Notification } from '../../api/notifications'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

const CHANNEL_AR: Record<string, string> = {
  in_app: 'داخل التطبيق', sms: 'SMS', whatsapp: 'واتساب', email: 'بريد',
}
const CHANNEL_ICON: Record<string, string> = {
  in_app: 'notifications', sms: 'sms', whatsapp: 'chat', email: 'mail',
}
// Graceful fallback used only until the backend channel list loads (or if it fails).
const FALLBACK_CHANNELS: { code: string; label: string }[] = [
  { code: 'in_app', label: 'داخل التطبيق' }, { code: 'sms', label: 'SMS' },
  { code: 'whatsapp', label: 'واتساب' }, { code: 'email', label: 'بريد' },
]

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
  const [channels, setChannels] = useState<{ code: string; label: string }[]>(FALLBACK_CHANNELS)

  const load = useCallback(async () => {
    setLoading(true); setError(null)
    try { const r = await listNotifications(); setRows(r.items); setUnread(r.unread) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  // Delivery channels are loaded from the backend; falls back to the seed on failure.
  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const r = await listChannels()
        if (alive && r.items.length) setChannels(r.items)
      } catch {
        /* keep FALLBACK_CHANNELS */
      }
    })()
    return () => { alive = false }
  }, [])

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
          <div className="flex flex-col gap-space-sm">
            {rows.map((n) => (
              <button key={n.id} onClick={() => !n.is_read && readOne(n.id)} disabled={n.is_read}
                className={`group w-full text-start rounded-2xl border p-space-md flex items-start gap-space-md transition-shadow ${
                  n.is_read
                    ? 'bg-surface-container-lowest border-surface-container-high opacity-70'
                    : 'bg-surface-container-lowest border-gold/40 shadow-card hover:shadow-overlay'
                }`}>
                <span className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${n.is_read ? 'bg-surface-variant text-secondary' : 'bg-brand-weak text-primary'}`}>
                  <Icon name={CHANNEL_ICON[n.channel] ?? 'notifications'} size={20} />
                </span>
                <div className="flex flex-col gap-space-xs min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-space-sm">
                    <span className="font-body-medium text-body-medium text-on-surface truncate">{n.title}</span>
                    <div className="flex items-center gap-space-xs shrink-0">
                      <Pill tone="neutral">{CHANNEL_AR[n.channel] ?? n.channel}</Pill>
                      {!n.is_read && <span className="w-2 h-2 rounded-full bg-gold" />}
                    </div>
                  </div>
                  {n.body && <span className="font-body text-body text-secondary">{n.body}</span>}
                  <span className="font-mono-body text-mono-body text-secondary" dir="ltr">{formatDate(n.created_at)}</span>
                </div>
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
                {channels.map((c) => (
                  <button key={c.code} type="button" onClick={() => setForm({ ...form, channel: c.code })}
                    className={`px-3 py-1 rounded-full font-small ${form.channel === c.code ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant'}`}>
                    {c.label}
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
