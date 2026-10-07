import { API_BASE, ApiError, api, tokenStore } from './client'

export interface AsstConversation {
  id: number
  title: string | null
  updated_at?: string
}
export interface AsstMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  meta?: {
    citations?: string[]
    top_score?: number
    mode?: string
    knowledge_gap?: boolean
    route?: string | null
    capped?: boolean
  } | null
  created_at?: string
}
export interface AssistantStatus {
  index: {
    version: number | null
    ready: boolean
    degraded: boolean | null
    doc_count: number
    chunk_count: number
    indexed_at: string | null
  }
  deepseek: { configured: boolean; model: string; mode: 'live' | 'mock' }
  usage: { messages_today: number; daily_cap: number }
  retrieval_available: boolean
}
export interface KnowledgeGap {
  id: number
  question: string
  route: string | null
  status: string
  answer: string | null
  created_at: string
}

export async function createConversation(title?: string) {
  return api<{ id: number; title: string | null }>('/assistant/conversations', {
    method: 'POST',
    body: { title },
  })
}
export async function listConversations() {
  return api<{ items: AsstConversation[] }>('/assistant/conversations')
}
export async function getConversation(id: number) {
  return api<{ id: number; title: string | null; messages: AsstMessage[] }>(
    `/assistant/conversations/${id}`,
  )
}
export async function getStatus() {
  return api<AssistantStatus>('/assistant/status')
}
export async function listGaps(status = 'open') {
  return api<{ items: KnowledgeGap[] }>('/assistant/gaps', { query: { status } })
}
export async function answerGap(id: number, answer: string) {
  return api<{ id: number; status: string }>(`/assistant/gaps/${id}/answer`, {
    method: 'POST',
    body: { answer },
  })
}

/** Upload a screenshot/PDF; the server extracts + redacts text locally and
 *  returns only the cleaned text (the file never leaves the server). */
export async function uploadForText(file: File) {
  const form = new FormData()
  form.append('file', file)
  const headers: Record<string, string> = {}
  const token = tokenStore.getAccess()
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${API_BASE}/assistant/upload`, { method: 'POST', headers, body: form })
  if (!res.ok) {
    const j = (await res.json().catch(() => null)) as { error?: string; message?: string } | null
    throw new ApiError(res.status, j?.error ?? 'upload_failed', j?.message ?? 'تعذّر رفع الملف')
  }
  return (await res.json()) as { text: string; redaction: Record<string, number> }
}

/**
 * Ask a question and stream the answer. Calls `onDelta` with each text chunk as
 * it arrives (first token in <3s). Resolves when the stream ends.
 */
/** Abort the request if nothing arrives within this window (a dead/stalled
 *  connection), so the UI fails fast with a clear message instead of freezing. */
const STALL_MS = 45_000

export async function askStream(
  conversationId: number,
  body: { question: string; route?: string | null },
  onDelta: (text: string) => void,
  signal?: AbortSignal,
): Promise<void> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  const token = tokenStore.getAccess()
  if (token) headers.Authorization = `Bearer ${token}`

  // Internal controller: aborts on the external signal OR on a stall timeout.
  const ctrl = new AbortController()
  let timedOut = false
  if (signal) {
    if (signal.aborted) ctrl.abort()
    else signal.addEventListener('abort', () => ctrl.abort(), { once: true })
  }
  let stall: ReturnType<typeof setTimeout>
  const arm = () => {
    clearTimeout(stall)
    stall = setTimeout(() => { timedOut = true; ctrl.abort() }, STALL_MS)
  }

  try {
    arm()
    const res = await fetch(`${API_BASE}/assistant/conversations/${conversationId}/ask`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })
    if (!res.ok || !res.body) {
      const j = (await res.json().catch(() => null)) as { error?: string; message?: string } | null
      throw new ApiError(res.status, j?.error ?? 'ask_failed', j?.message ?? 'تعذّر الحصول على إجابة')
    }
    const reader = res.body.getReader()
    const decoder = new TextDecoder('utf-8')
    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      arm() // reset the stall timer on every chunk
      const text = decoder.decode(value, { stream: true })
      if (text) onDelta(text)
    }
  } catch (err) {
    if (timedOut) {
      throw new ApiError(408, 'timeout', 'انتهت مهلة الاتصال بالمساعد. تأكد من تشغيل الخادم وحاول مجددًا.')
    }
    throw err
  } finally {
    clearTimeout(stall!)
  }
}
