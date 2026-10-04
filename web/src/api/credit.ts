import { api } from './client'

export interface CreditTier {
  customer_id: number
  tier: string
  score: string | null
  credit_limit_default: string
  effective_limit: string
  deferred_pct: string
  outstanding: string
}
export interface Escalation {
  id: number
  customer_id: number
  level: number
  trigger_reason: string
  is_automatic: boolean
  actor_user_id: number | null
  triggered_at: string
}
export interface TierSetting {
  tier: string
  credit_limit: string
  deferred_pct: string
}
export interface PaymentApproval {
  id: number
  customer_id: number
  due_id: number | null
  amount: string
  paid_on: string
  collected_by: number
  status: string
  approved_by: number | null
  approved_at: string | null
  note: string | null
}

export async function getCustomerCredit(id: number) {
  return api<CreditTier>(`/credit/customers/${id}`)
}
export async function recomputeCredit(id: number) {
  return api<CreditTier>(`/credit/customers/${id}/recompute`, { method: 'POST' })
}
export async function setOverride(customer_id: number, credit_limit: string, reason: string) {
  return api<{ id: number }>('/credit/overrides', { method: 'POST', body: { customer_id, credit_limit, reason } })
}
export async function listEscalations(id: number) {
  return api<{ items: Escalation[] }>(`/credit/customers/${id}/escalations`)
}
export async function runEscalation() {
  return api<{ opened: number }>('/credit/escalation/run', { method: 'POST' })
}
export async function freezeCustomer(id: number, reason: string) {
  return api<Escalation>(`/credit/customers/${id}/freeze`, { method: 'POST', body: { reason } })
}
export async function payDue(dueId: number, paid_on: string) {
  return api<{ id: number; status: string; days_late: number }>(`/credit/dues/${dueId}/pay`, { method: 'POST', body: { paid_on } })
}

export async function listTierSettings() {
  return api<{ items: TierSetting[] }>('/credit/tier-settings')
}
export async function setTierSetting(tier: string, credit_limit: string, deferred_pct: string) {
  return api<TierSetting>(`/credit/tier-settings/${tier}`, { method: 'PUT', body: { credit_limit, deferred_pct } })
}

export async function listPayments(status?: string) {
  return api<{ items: PaymentApproval[] }>('/credit/payments', { query: status ? { status } : undefined })
}
export async function collectPayment(body: { customer_id: number; due_id?: number; amount: string; paid_on: string }) {
  return api<PaymentApproval>('/credit/payments/collect', { method: 'POST', body })
}
export async function approvePayment(id: number) {
  return api<PaymentApproval>(`/credit/payments/${id}/approve`, { method: 'POST' })
}
export async function rejectPayment(id: number, reason: string) {
  return api<PaymentApproval>(`/credit/payments/${id}/reject`, { method: 'POST', body: { reason } })
}
