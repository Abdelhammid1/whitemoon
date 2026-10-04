import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { Button, Spinner, InlineError } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { useToast } from '../../components/Toast'
import { listMessages, sendMessage, type Message } from '../../api/comm'
import { ApiError } from '../../api/client'
import { formatDate } from '../../lib/format'

function roleLabel(role: string) {
  return role === 'customer' ? 'العميل' : role === 'supplier' ? 'المورّد' : 'الإدارة'
}

/** One message row — mine (end, solid) vs theirs (start, raised), or a blocked notice. */
function MessageRow({ m }: { m: Message }) {
  if (m.status === 'blocked') {
    return (
      <div className="flex flex-col items-end self-end max-w-[85%] w-full">
        <div className="flex items-center gap-space-xs mb-1">
          <span className="font-mono-body text-mono-body text-error" dir="ltr">
            {formatDate(m.created_at)}
          </span>
          <span className="font-small-medium text-small-medium text-error">رسالة محجوبة آلياً</span>
        </div>
        <div className="p-space-md rounded bg-error-container text-on-error-container w-full max-w-[620px]">
          <div className="flex items-start gap-space-sm">
            <Icon name="block" size={20} className="text-error shrink-0 mt-0.5" />
            <div className="flex flex-col gap-1 w-full">
              <span className="font-body-medium text-body-medium text-error">
                حُجبت: محاولة تبادل بيانات اتصال
              </span>
              <p className="font-body text-body text-on-error-container leading-relaxed">
                لم يتم تسليم الرسالة للطرف الآخر وفق سياسات المنصة، وسُجِّل التنبيه في سجل الامتثال.
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (m.mine) {
    return (
      <div className="flex flex-col items-end self-end max-w-[78%]">
        <div className="flex items-center gap-space-xs mb-1">
          <span className="font-mono-body text-mono-body text-secondary" dir="ltr">
            {formatDate(m.created_at)}
          </span>
          <span className="font-small-medium text-small-medium text-primary">أنا</span>
        </div>
        <div className="p-space-md rounded bg-primary text-on-primary font-body text-body leading-relaxed whitespace-pre-wrap">
          {m.body}
          {m.image_url && (
            <div className="mt-space-sm flex items-center gap-1.5 font-mono-body text-mono-body opacity-80">
              <Icon name="attach_file" size={14} />
              <span>صورة مرفقة</span>
            </div>
          )}
        </div>
        <div className="flex items-center gap-1 mt-1 text-secondary font-mono-body text-mono-body">
          <Icon name="done_all" size={14} />
          <span className="text-[11px]">مُرسل عبر بوابة الوساطة</span>
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col items-start max-w-[78%]">
      <div className="flex items-center gap-space-xs mb-1">
        <span className="font-small-medium text-small-medium text-primary">{roleLabel(m.sender_role)}</span>
        <span className="font-mono-body text-mono-body text-secondary" dir="ltr">
          {formatDate(m.created_at)}
        </span>
      </div>
      <div className="p-space-md rounded bg-surface-container-low text-on-surface font-body text-body leading-relaxed whitespace-pre-wrap">
        {m.body}
        {m.image_url && (
          <div className="mt-space-sm flex items-center gap-1.5 p-space-sm bg-surface-container-lowest rounded border-b border-surface-container-highest font-mono-body text-mono-body text-secondary">
            <Icon name="description" size={18} className="text-primary" />
            <span>صورة مرفقة — تم التحقق آلياً من المحتوى</span>
          </div>
        )}
      </div>
      <span className="font-small text-small text-secondary mt-1">مُسلَّمة عبر بوابة الوساطة</span>
    </div>
  )
}

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
  if (error)
    return (
      <Narrow>
        <div className="mt-space-xl flex flex-col items-center justify-center py-20 text-center">
          <div className="w-12 h-12 rounded bg-error-container text-error flex items-center justify-center mb-space-md">
            <Icon name="wifi_off" size={28} />
          </div>
          <h2 className="font-headline-1 text-headline-1 text-primary">تعذّر تحميل المحادثة</h2>
          <div className="mt-space-md w-full max-w-[480px]"><InlineError message={error} /></div>
        </div>
      </Narrow>
    )

  return (
    <Narrow>
      {/* Breadcrumb / context bar */}
      <div className="flex items-center justify-between pb-space-md border-b border-surface-container-highest">
        <div className="flex items-center gap-space-sm">
          <span className="font-small-medium text-small-medium text-secondary">المحادثات النشطة</span>
          <span className="text-surface-container-highest">/</span>
          <span className="font-mono-body text-mono-body text-on-surface-variant" dir="ltr">#{cid}</span>
        </div>
        <div className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-surface-container text-on-surface-variant font-mono-medium text-mono-medium">
          <span className="w-1.5 h-1.5 rounded-full bg-primary" />
          <span className="tracking-tight" dir="ltr">SECURE_MEDIATION: ON</span>
        </div>
      </div>

      {/* Mandatory mediation banner */}
      <div className="mt-space-md p-space-md bg-surface-container-low rounded flex items-start gap-space-sm border-r-2 border-primary">
        <Icon name="policy" size={20} className="text-primary shrink-0 mt-0.5" />
        <div className="flex flex-col gap-0.5">
          <span className="font-body-medium text-body-medium text-primary">
            كل الرسائل تمر عبر الشركة وتخضع للرقابة الآلية
          </span>
          <p className="font-small text-small text-secondary leading-relaxed">
            يُفحص النص والمرفقات فورياً لمنع تداول أرقام الهواتف أو قنوات التواصل المباشر، وهوية الطرف
            الآخر محجوبة نظامياً.
          </p>
        </div>
      </div>

      {/* Masked peer header */}
      <div className="mt-space-md p-space-md flex items-center gap-space-md border-b border-surface-container-highest">
        <div className="w-12 h-12 rounded bg-surface-container flex items-center justify-center text-primary font-mono-medium text-[16px] font-medium">
          <Icon name="shield_person" size={22} />
        </div>
        <div className="flex flex-col">
          <h1 className="font-headline-1 text-headline-1 text-primary">الطرف الآخر</h1>
          <span className="font-small text-small text-secondary mt-0.5">
            هوية الطرف محجوبة — تظهر الصفة فقط مع كل رسالة
          </span>
        </div>
      </div>

      {/* Messages canvas */}
      <div className="flex flex-col gap-space-lg py-space-lg min-h-[40vh]">
        {msgs.length === 0 ? (
          <div className="flex items-center justify-center py-16">
            <span className="font-body text-body text-secondary">لا توجد رسائل بعد.</span>
          </div>
        ) : (
          msgs.map((m) => <MessageRow key={m.id} m={m} />)
        )}
        <div ref={endRef} />
      </div>

      {/* Composer */}
      <form onSubmit={send} className="mt-space-lg pt-space-md border-t border-surface-container-highest flex flex-col gap-space-sm">
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          rows={3}
          placeholder="اكتب رسالتك التنسيقية هنا… (تجنّب ذكر أرقام الهواتف أو قنوات التواصل الخارجية)"
          className="w-full bg-transparent border-0 border-b border-surface-container-highest focus:border-primary focus:border-b-2 focus:outline-none py-space-sm px-0 font-body text-body text-on-surface placeholder:text-outline transition-colors resize-none"
        />
        <div className="flex items-center justify-between pt-space-xs">
          <div className="flex items-center gap-1.5 text-secondary font-small text-small">
            <Icon name="shield" size={14} />
            <span>يُفحص النص والصور آلياً لمنع تسريب بيانات الاتصال.</span>
          </div>
          <Button variant="primary" type="submit" iconRight="send" disabled={busy || !body.trim()}>
            إرسال الرسالة
          </Button>
        </div>
      </form>
    </Narrow>
  )
}
