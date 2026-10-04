import { api } from './client'

export interface Conversation {
  id: number
  order_id: number | null
  subject: string | null
  status: string
  counterpart_role?: string
  customer_id?: number
  supplier_id?: number
  flagged?: boolean
}
export interface Message {
  id: number
  conversation_id: number
  sender_role: string
  mine: boolean
  body: string | null
  image_url: string | null
  status: string
  created_at: string
  block_reason?: string
  sender_id?: number
}

export async function listConversations(params: { status?: string; flagged?: boolean } = {}) {
  return api<{ items: Conversation[] }>('/comm/conversations', {
    query: { status: params.status, flagged: params.flagged ? 'true' : undefined },
  })
}
export async function startConversation(body: { customer_id: number; supplier_id: number; order_id?: number; subject?: string }) {
  return api<Conversation>('/comm/conversations', { method: 'POST', body })
}
export async function listMessages(id: number) {
  return api<{ items: Message[] }>(`/comm/conversations/${id}/messages`)
}
export async function sendMessage(id: number, body: { body?: string; image_b64?: string }) {
  return api<Message>(`/comm/conversations/${id}/messages`, { method: 'POST', body })
}
