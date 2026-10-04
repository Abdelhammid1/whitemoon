import { api } from './client'

export interface AdminUser {
  id: number
  phone: string | null
  email: string | null
  kind: string
  status: string
  created_at: string
}

export interface PendingSupplier {
  user_id: number
  legal_name: string
  commercial_register_no: string
  tax_card_no: string
  national_id: string
  created_at: string
}

export async function listUsers(params: {
  q?: string
  kind?: string
  status?: string
  limit?: number
}) {
  return api<{ items: AdminUser[] }>('/admin/users', {
    query: params,
  })
}

export interface UserDetail extends AdminUser {
  activated_at: string | null
  roles: string[]
}
export async function getUser(userId: number) {
  return api<UserDetail>(`/admin/users/${userId}`)
}

export interface AuditRow {
  id: number
  at: string
  actor_user_id: number | null
  action: string
  target_type: string | null
  target_id: string | null
  reason: string | null
}
export async function listAudit(params: { action?: string; limit?: number } = {}) {
  return api<{ items: AuditRow[] }>('/admin/audit', { query: params })
}

export async function listPendingSuppliers() {
  return api<{ items: PendingSupplier[] }>('/admin/suppliers/pending')
}

export async function approveSupplier(userId: number) {
  return api<{ user_id: number; status: string }>(`/admin/suppliers/${userId}/approve`, {
    method: 'POST',
  })
}

export async function rejectSupplier(userId: number, reason: string) {
  return api<{ user_id: number; status: string }>(`/admin/suppliers/${userId}/reject`, {
    method: 'POST',
    body: { reason },
  })
}

export async function startImpersonation(target_user_id: number, reason: string) {
  return api<{
    grant_id: number
    access_token: string
    acting_as_user_id: number
    admin_user_id: number
  }>('/admin/impersonate/start', {
    method: 'POST',
    body: { target_user_id, reason },
  })
}

export async function stopImpersonation(grantId: number) {
  return api<{ status: string }>(`/admin/impersonate/${grantId}/stop`, {
    method: 'POST',
  })
}
