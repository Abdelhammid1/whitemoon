import { api } from './client'

export interface Notification {
  id: number
  type: string
  title: string
  body: string | null
  channel: string
  is_read: boolean
  created_at: string
}

export async function listNotifications(unread = false) {
  return api<{ items: Notification[]; unread: number }>('/notifications', {
    query: unread ? { unread: 'true' } : undefined,
  })
}
export async function markRead(id: number) {
  return api<Notification>(`/notifications/${id}/read`, { method: 'POST' })
}
export async function markAllRead() {
  return api<{ marked: number }>('/notifications/read-all', { method: 'POST' })
}
/** Delivery channels (code + Arabic label) from the backend — the UI's single source. */
export async function listChannels() {
  return api<{ items: { code: string; label: string }[] }>('/notifications/channels')
}
export async function sendNotification(body: {
  user_id: number
  title: string
  body?: string
  type?: string
  channel?: string
}) {
  return api<Notification>('/notifications', { method: 'POST', body })
}
