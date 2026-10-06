import { api, openDocument, postForm } from './client'

export interface CreditTier {
  customer_id: number
  tier: string
  score: string | null
  credit_limit_default: string
  effective_limit: string
  deferred_pct: string
  outstanding: string
  order_block_level: number // 0 none · 2 block deferred + 50% cut · 4 freeze all orders
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
  source?: string
  has_receipt?: boolean
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
export interface Due {
  id: number
  order_id: number | null
  amount: string
  due_date: string
  status: string
  paid_date: string | null
  days_late: number | null
}
export async function listDues(customerId: number) {
  return api<{ items: Due[] }>(`/credit/customers/${customerId}/dues`)
}

export interface DunningRow {
  customer_id: number
  display_name: string | null
  tier: string
  outstanding: string
  open_due_count: number
  worst_overdue_days: number
  order_block_level: number
}
export async function listDunning(params: { min_days?: number; tier?: string } = {}) {
  return api<{ items: DunningRow[] }>('/credit/dunning', {
    query: {
      min_days: params.min_days != null ? String(params.min_days) : undefined,
      tier: params.tier,
    },
  })
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

/** T-21: a customer uploads a bank-transfer receipt image (multipart). */
export async function uploadReceipt(body: { image: File; amount: string; due_id?: number; paid_on?: string }) {
  const form = new FormData()
  form.append('image', body.image)
  form.append('amount', body.amount)
  if (body.due_id != null) form.append('due_id', String(body.due_id))
  if (body.paid_on) form.append('paid_on', body.paid_on)
  return postForm<PaymentApproval>('/credit/payments/upload-receipt', form)
}
/** A customer's own submitted receipts / payments. */
export async function myPayments() {
  return api<{ items: PaymentApproval[] }>('/credit/payments/mine')
}
/** Open a payment's receipt image in a new tab (auth'd). */
export async function openReceipt(id: number) {
  return openDocument(`/credit/payments/${id}/receipt`)
}
