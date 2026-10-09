import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from 'react'
import { Button, Pill } from '../ui'
import { Icon } from '../Icon'
import { Markdown } from '../Markdown'
import { useToast } from '../Toast'
import { ApiError } from '../../api/client'
import {
  askStream,
  createConversation,
  getConversation,
  sendFeedback,
  uploadForText,
  type AsstMessage,
} from '../../api/assistant'

interface Props {
  route?: string | null
  compact?: boolean
  /** Continue an existing conversation (and preload its history). */
  conversationId?: number | null
  initialMessages?: AsstMessage[]
  /** Fired when a new conversation is created, so a parent list can refresh. */
  onConversationCreated?: (id: number) => void
}

const REDACT_AR: Record<string, string> = {
  email: 'بريد',
  phone: 'هاتف',
  amount: 'مبلغ',
  tax_id: 'رقم',
  number: 'رقم',
  token: 'مفتاح',
}

const STARTERS_HINT = 'اسأل عن أي دور أو شاشة أو خطوة في المنظومة — مثلاً: «إزاي أضيف فرع؟»'

export interface AssistantChatHandle {
  ask: (question: string) => void
}

export const AssistantChat = forwardRef<AssistantChatHandle, Props>(function AssistantChat({
  route,
  compact = false,
  conversationId = null,
  initialMessages,
  onConversationCreated,
}: Props, ref) {
  const toast = useToast()
  const [convId, setConvId] = useState<number | null>(conversationId)
  const [messages, setMessages] = useState<AsstMessage[]>(initialMessages ?? [])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [redactNote, setRedactNote] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Reset when the parent switches to a different (or new) conversation.
  useEffect(() => {
    setConvId(conversationId)
    setMessages(initialMessages ?? [])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [conversationId])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages])

  useImperativeHandle(ref, () => ({ ask: (q: string) => void send(q) }))

  const lastAssistantEmpty =
    streaming && messages.length > 0 && messages[messages.length - 1]?.role === 'assistant' &&
    messages[messages.length - 1]?.content === ''

  async function send(question: string) {
    const q = question.trim()
    if (!q || streaming) return
    setInput('')
    setRedactNote(null)
    setMessages((prev) => [
      ...prev,
      { role: 'user', content: q },
      { role: 'assistant', content: '' },
    ])
    setStreaming(true)
    const ctrl = new AbortController()
    abortRef.current = ctrl
    try {
      let id = convId
      if (id == null) {
        id = (await createConversation()).id
        setConvId(id)
        onConversationCreated?.(id)
      }
      await askStream(
        id,
        { question: q, route: route ?? null },
        (delta) =>
          setMessages((prev) => {
            const copy = [...prev]
            const last = copy[copy.length - 1]
            if (last && last.role === 'assistant') copy[copy.length - 1] = { ...last, content: last.content + delta }
            return copy
          }),
        ctrl.signal,
      )
      // Replace optimistic state with the server's truth (redacted question +
      // assistant meta: citations / knowledge-gap flag).
      try {
        const full = await getConversation(id)
        setMessages(full.messages)
      } catch {
        /* keep streamed text if the refetch fails */
      }
    } catch (err) {
      if (!(err instanceof DOMException && err.name === 'AbortError')) {
        toast.error(err instanceof ApiError ? err.message : 'حدث خطأ')
        setMessages((prev) => prev.filter((m, i) => !(i === prev.length - 1 && m.role === 'assistant' && m.content === '')))
      }
    } finally {
      setStreaming(false)
      abortRef.current = null
    }
  }

  function stop() {
    abortRef.current?.abort()
  }

  async function onFile(file: File) {
    try {
      const res = await uploadForText(file)
      setInput((prev) => (prev ? prev + '\n' : '') + res.text.trim())
      const note = Object.entries(res.redaction)
        .map(([k, v]) => `${REDACT_AR[k] ?? k} ×${v}`)
        .join('، ')
      setRedactNote(note ? `حُجب تلقائيًا: ${note}` : 'لم يُعثر على بيانات حساسة في الملف.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر قراءة الملف')
    }
  }

  async function handleFeedback(question: string, answer: string) {
    if (convId == null) return
    await sendFeedback(convId, { question, answer, route: route ?? null })
  }

  const pad = compact ? 'p-space-sm' : 'p-space-md'
  const gap = compact ? 'gap-space-sm' : 'gap-space-md'

  return (
    <div className="flex h-full flex-col">
      {/* messages */}
      <div ref={scrollRef} className={`flex-1 overflow-y-auto flex flex-col ${gap} ${pad}`}>
        {messages.length === 0 && (
          <div className="m-auto max-w-[460px] text-center text-on-surface-variant">
            <Icon name="smart_toy" size={40} className="text-primary" />
            <p className="mt-space-sm font-body text-body">{STARTERS_HINT}</p>
          </div>
        )}
        {messages.map((m, i) => (
          <MessageBubble
            key={i}
            message={m}
            compact={compact}
            onFeedback={
              m.role === 'assistant' && m.content && convId != null && !streaming
                ? () => handleFeedback(messages[i - 1]?.content ?? '', m.content)
                : undefined
            }
          />
        ))}
        {lastAssistantEmpty && (
          <div className="flex items-center gap-space-sm px-space-sm font-small text-small text-secondary">
            <Icon name="more_horiz" size={18} className="animate-pulse text-primary" /> يكتب…
          </div>
        )}
      </div>

      {/* composer */}
      <div className={`border-t border-surface-container-high ${pad} flex flex-col gap-space-xs`}>
        <div className="flex items-center gap-space-xs font-small text-small text-warning">
          <Icon name="info" size={14} /> لا ترفع صورة أو ملف فيه بيانات عملاء.
        </div>
        {redactNote && (
          <div className="font-small text-small text-signal">{redactNote}</div>
        )}
        <div className="flex items-end gap-space-sm">
          <input
            ref={fileRef}
            type="file"
            accept="image/*,.pdf"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0]
              if (f) void onFile(f)
              e.target.value = ''
            }}
          />
          <button
            type="button"
            title="إرفاق صورة/ملف"
            onClick={() => fileRef.current?.click()}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-lg border border-surface-container-high text-primary hover:bg-surface-container-low"
          >
            <Icon name="attach_file" size={18} />
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                void send(input)
              }
            }}
            rows={compact ? 2 : 2}
            placeholder="اكتب سؤالك…"
            className="flex-1 resize-none rounded-lg border border-surface-container-high bg-surface-container-lowest px-space-md py-space-sm font-body text-body text-on-surface focus:border-primary focus:outline-none"
          />
          {streaming ? (
            <Button variant="destructive" onClick={stop} iconRight="stop" className="shrink-0">
              <span className="hidden sm:inline">إيقاف</span>
            </Button>
          ) : (
            <Button variant="primary" onClick={() => void send(input)} disabled={!input.trim()} iconRight="send" className="shrink-0">
              <span className="hidden sm:inline">إرسال</span>
            </Button>
          )}
        </div>
      </div>
    </div>
  )
})

function MessageBubble({
  message,
  compact,
  onFeedback,
}: {
  message: AsstMessage
  compact: boolean
  onFeedback?: () => Promise<void>
}) {
  const isUser = message.role === 'user'
  const gap = message.meta?.knowledge_gap
  const citations = message.meta?.citations ?? []
  const toast = useToast()
  const [fbSent, setFbSent] = useState(false)
  const [fbBusy, setFbBusy] = useState(false)

  async function flagNotHelpful() {
    if (!onFeedback || fbBusy || fbSent) return
    setFbBusy(true)
    try {
      await onFeedback()
      setFbSent(true)
      toast.success('شكرًا — سجّلنا إن الإجابة لم تفد لمراجعتها.')
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر تسجيل الملاحظة')
    } finally {
      setFbBusy(false)
    }
  }

  return (
    <div className="flex flex-col gap-space-xs">
      <div className="flex items-center gap-space-xs font-small text-small text-secondary">
        <Icon name={isUser ? 'person' : 'smart_toy'} size={16} className={isUser ? '' : 'text-primary'} />
        {isUser ? 'أنت' : 'المساعد'}
      </div>
      <div
        className={`rounded-2xl ${compact ? 'px-space-md py-space-sm' : 'p-space-md'} font-body text-body break-words ${
          isUser
            ? 'bg-brand-weak text-on-surface whitespace-pre-wrap'
            : 'bg-surface-container-lowest border border-surface-container-high text-on-surface shadow-card-sm'
        }`}
      >
        {isUser ? (
          message.content || '…'
        ) : message.content ? (
          <Markdown>{message.content}</Markdown>
        ) : (
          '…'
        )}
      </div>
      {!isUser && gap && (
        <div className="flex items-center gap-space-xs font-small text-small text-warning">
          <Icon name="help" size={14} /> لم أجد معلومات كافية — سُجِّل كفجوة معرفة للمراجعة.
        </div>
      )}
      {!isUser && citations.length > 0 && (
        <div className="flex flex-wrap gap-space-xs">
          {citations.slice(0, 6).map((c, i) => (
            <Pill key={i} tone="neutral">{c}</Pill>
          ))}
        </div>
      )}
      {!isUser && onFeedback && (
        <button
          type="button"
          onClick={flagNotHelpful}
          disabled={fbBusy || fbSent}
          className="self-start inline-flex items-center gap-space-xs font-small text-small text-secondary transition-colors hover:text-danger disabled:opacity-60"
        >
          <Icon name={fbSent ? 'check' : 'thumb_down'} size={14} />
          {fbSent ? 'شكرًا لملاحظتك' : 'الإجابة لم تفد'}
        </button>
      )}
    </div>
  )
}
