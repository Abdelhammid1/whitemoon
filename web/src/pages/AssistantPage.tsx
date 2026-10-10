import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { Button, Pill } from '../components/ui'
import { Icon } from '../components/Icon'
import { PageHelp } from '../components/PageHelp'
import { useToast } from '../components/Toast'
import { ApiError } from '../api/client'
import { formatDateTime } from '../lib/format'
import {
  getConversation,
  getStatus,
  listConversations,
  type AssistantStatus,
  type AsstConversation,
  type AsstMessage,
} from '../api/assistant'
import { AssistantChat, type AssistantChatHandle } from '../components/assistant/AssistantChat'

const STARTERS = [
  'ما وظيفة الوكيل في النظام؟',
  'إزاي أضيف فرع جديد؟',
  'إيه الفرق بين الوكيل والفرع؟',
  'إزاي المورد بيتعامل مع النظام؟',
]

export function AssistantPage() {
  const toast = useToast()
  const chatRef = useRef<AssistantChatHandle>(null)
  const [status, setStatus] = useState<AssistantStatus | null>(null)
  const [convs, setConvs] = useState<AsstConversation[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [initialMessages, setInitialMessages] = useState<AsstMessage[]>([])
  const [newNonce, setNewNonce] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  async function refreshConvs() {
    try {
      setConvs((await listConversations()).items)
    } catch {
      /* non-fatal */
    }
  }

  useEffect(() => {
    void refreshConvs()
    getStatus().then(setStatus).catch(() => setStatus(null))
  }, [])

  async function openConversation(id: number) {
    try {
      const full = await getConversation(id)
      setSelectedId(id)
      setInitialMessages(full.messages)
      setSidebarOpen(false)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر فتح المحادثة')
    }
  }

  function newConversation() {
    setSelectedId(null)
    setInitialMessages([])
    setNewNonce((n) => n + 1)
    setSidebarOpen(false)
  }

  const chatKey = selectedId != null ? `c${selectedId}` : `new${newNonce}`

  const Sidebar = (
    <div className="flex h-full flex-col gap-space-sm">
      <Button variant="primary" onClick={newConversation} iconRight="add" className="w-full">
        محادثة جديدة
      </Button>
      <div className="flex-1 overflow-y-auto flex flex-col gap-space-xs">
        {convs.length === 0 ? (
          <p className="px-space-sm py-space-md font-small text-small text-secondary">لا توجد محادثات بعد.</p>
        ) : (
          convs.map((c) => (
            <button
              key={c.id}
              type="button"
              onClick={() => void openConversation(c.id)}
              className={`text-start truncate rounded-lg px-space-md py-space-sm font-small text-small transition-colors ${
                selectedId === c.id
                  ? 'bg-brand-weak text-primary'
                  : 'text-on-surface-variant hover:bg-surface-container-low'
              }`}
            >
              {c.title || 'محادثة'}
              {c.updated_at && (
                <span className="block font-small text-[11px] text-outline">{formatDateTime(c.updated_at)}</span>
              )}
            </button>
          ))
        )}
      </div>
    </div>
  )

  return (
    <div dir="rtl" className="flex h-screen flex-col bg-background text-on-surface font-body">
      {/* top bar */}
      <header className="sticky top-0 z-30 shrink-0 border-b border-surface-container-high bg-background/85 backdrop-blur">
        <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-space-md px-gutter py-space-sm">
          <div className="flex items-center gap-space-md">
            <button
              type="button"
              onClick={() => setSidebarOpen((o) => !o)}
              aria-label="المحادثات"
              className="grid h-9 w-9 place-items-center rounded-lg border border-surface-container-high text-primary lg:hidden"
            >
              <Icon name="menu" size={20} />
            </button>
            <Brand size={26} />
            <span className="hidden font-small text-small text-on-surface-variant sm:block">مساعد المدير</span>
          </div>
          <div className="flex items-center gap-space-sm">
            <StatusBadges status={status} />
            <Link to="/home">
              <Button iconRight="arrow_back"><span className="hidden sm:inline">لوحة التحكم</span></Button>
            </Link>
          </div>
        </div>
      </header>

      <div className="mx-auto flex w-full max-w-[1280px] flex-1 gap-space-md overflow-hidden px-gutter py-space-md">
        {/* desktop sidebar */}
        <aside className="hidden w-[260px] shrink-0 lg:block">
          <div className="h-full rounded-2xl border border-surface-container-high bg-surface-container-lowest p-space-md shadow-card-sm">
            {Sidebar}
          </div>
        </aside>

        {/* mobile sidebar drawer */}
        {sidebarOpen && (
          <>
            <div className="fixed inset-0 z-30 bg-inverse-surface/30 lg:hidden" onClick={() => setSidebarOpen(false)} />
            <aside className="fixed inset-y-0 right-0 z-40 w-[280px] overflow-y-auto border-l border-surface-container-high bg-surface-container-lowest p-space-md pt-[72px] shadow-overlay lg:hidden">
              {Sidebar}
            </aside>
          </>
        )}

        {/* main */}
        <main className="flex min-w-0 flex-1 flex-col gap-space-sm">
          <PageHelp pageKey="assistant" />
          <div className="flex flex-wrap gap-space-xs">
            {STARTERS.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => chatRef.current?.ask(s)}
                className="rounded-full border border-surface-container-high bg-surface-container-lowest px-space-md py-space-xs font-small text-small text-primary hover:bg-surface-container-low"
              >
                {s}
              </button>
            ))}
          </div>
          <div className="min-h-0 flex-1 overflow-hidden rounded-2xl border border-surface-container-high bg-surface-container-lowest shadow-card">
            <AssistantChat
              key={chatKey}
              ref={chatRef}
              route={null}
              conversationId={selectedId}
              initialMessages={initialMessages}
              onConversationCreated={() => void refreshConvs()}
            />
          </div>
        </main>
      </div>
    </div>
  )
}

function StatusBadges({ status }: { status: AssistantStatus | null }) {
  if (!status) return null
  return (
    <div className="hidden items-center gap-space-xs md:flex">
      {status.deepseek.mode === 'mock' && <Pill tone="gold">وضع تجريبي</Pill>}
      {status.index.degraded && <Pill tone="warning">فهرسة مبدئية</Pill>}
      <span className="font-small text-small text-on-surface-variant">
        {status.index.ready ? `الفهرس v${status.index.version}` : 'لم يُفهرس بعد'}
        {' · '}
        اليوم {status.usage.messages_today}/{status.usage.daily_cap}
      </span>
    </div>
  )
}
