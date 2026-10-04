import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Spinner, InlineError } from '../../components/ui'
import { useToast } from '../../components/Toast'
import { listMessages, sendMessage, type Message } from '../../api/comm'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

export function ChatThreadPage() {
  const { id } = useParams()
  const cid = Number(id)
  const toast = useToast()
  const [msgs, setMsgs] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [body, setBody] = useState('')
  const [busy, setBusy] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  const load = useCallback(async () => {
    try { setMsgs((await listMessages(cid)).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [cid])
  useEffect(() => { void load() }, [load])
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  async function send(e: FormEvent) {
    e.preventDefault()
    if (!body.trim()) return
    setBusy(true)
    try {
      const m = await sendMessage(cid, { body })
      setBody('')
      await load()
      if (m.status === 'blocked') toast.error('حُجبت الرسالة: محاولة تبادل بيانات اتصال.')
    } catch (err) { toast.error(err instanceof ApiError ? err.message : 'تعذّر الإرسال') }
    finally { setBusy(false) }
  }

  if (loading) return <Narrow><Spinner /></Narrow>
  if (error) return <Narrow><div className="mt-space-xl"><InlineError message={error} /></div></Narrow>

  return (
    <Narrow>
      <PageTitle title={`محادثة #${cid}`} subtitle="كل الرسائل تمر عبر الشركة." />
      <div className="mt-space-lg flex flex-col gap-space-sm min-h-[40vh]">
        {msgs.map((m) => (
          <div key={m.id} className={`max-w-[80%] rounded-xl px-space-md py-space-sm ${m.mine ? 'self-end bg-primary text-on-primary' : 'self-start bg-surface-container'}`}>
            <div className="font-small text-small opacity-70 mb-1">
              {m.sender_role === 'customer' ? 'العميل' : m.sender_role === 'supplier' ? 'المورد' : 'الإدارة'} · {formatDate(m.created_at)}
            </div>
            {m.body && <div className="font-body text-body whitespace-pre-wrap">{m.body}</div>}
            {m.image_url && <div className="font-small text-small opacity-70">📎 صورة مرفقة</div>}
            {m.status === 'blocked' && (
              <div className="mt-1 font-small text-small text-[#ffb4ab]">حُجبت: محاولة تبادل بيانات اتصال</div>
            )}
          </div>
        ))}
        <div ref={endRef} />
      </div>

      <form onSubmit={send} className="mt-space-md flex items-end gap-space-sm border-t border-surface-container-high pt-space-md">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={2}
          placeholder="اكتب رسالتك…"
          className="flex-1 bg-transparent font-body text-body text-on-surface border border-surface-container-high rounded-lg p-space-sm focus:border-primary focus:outline-none resize-none"
        />
        <Button variant="primary" type="submit" disabled={busy || !body.trim()}>إرسال</Button>
      </form>
    </Narrow>
  )
}
