import { api } from './client'

export interface Partner {
  partner_id: number
  type: string
  display_name: string
  geo_scope: string | null
}
export interface PartnerTerms {
  partner_id: number
  earns_commission: boolean
  commission_rate_pct: string
  earns_investment_return: boolean
  investment_return_rate_pct: string
}
export interface Deposit {
  id: number
  partner_id: number
  amount: string
  deposit_date: string
  recovery_conditions: string
  status: string
  refunded_at: string | null
}
export interface Accrual {
  id: number
  partner_id: number
  kind: string
  period: string
  basis_amount: string
  rate_pct: string
  amount: string
  computed_at: string
}

export async function listPartners(type?: string) {
  return api<{ items: Partner[] }>('/partners', { query: type ? { type } : undefined })
}
export async function createPartner(body: {
  type: string; display_name: string; geo_scope?: string; phone?: string; email?: string; password: string
  earns_commission?: boolean; commission_rate_pct?: number
  earns_investment_return?: boolean; investment_return_rate_pct?: number
}) {
  return api<Partner>('/partners', { method: 'POST', body })
}
export async function getTerms(id: number) {
  return api<PartnerTerms>(`/partners/${id}/terms`)
}
export async function setTerms(id: number, body: {
  earns_commission: boolean; commission_rate_pct: number
  earns_investment_return: boolean; investment_return_rate_pct: number
}) {
  return api<PartnerTerms>(`/partners/${id}/terms`, { method: 'PUT', body })
}
export async function listDeposits(id: number) {
  return api<{ items: Deposit[] }>(`/partners/${id}/deposits`)
}
export async function recordDeposit(id: number, body: { amount: number; deposit_date: string; recovery_conditions: string }) {
  return api<Deposit>(`/partners/${id}/deposits`, { method: 'POST', body })
}
export async function refundDeposit(depositId: number, reason: string) {
  return api<Deposit>(`/partners/deposits/${depositId}/refund`, { method: 'POST', body: { reason } })
}
export async function listAccruals(id: number) {
  return api<{ items: Accrual[] }>(`/partners/${id}/accruals`)
}
export async function computeAccrual(id: number, kind: string, year: number, month: number) {
  return api<Accrual>(`/partners/${id}/accruals`, { method: 'POST', body: { kind, year, month } })
}

/* ---------------------------------------------------- current account (الحساب الجاري) */

export type LedgerKind = 'payment_made' | 'payment_received' | 'manual'

export interface LedgerEntry {
  id: number
  partner_id: number
  kind: LedgerKind
  direction: number // +1 raises "partner owes management", -1 lowers it
  amount: string
  note: string | null
  recorded_by: number
  created_at: string | null
}
export interface LedgerSummary {
  partner_id: number
  balance: string // signed, "partner owes management"
  abs_balance: string
  owed_by: 'partner' | 'management' | 'settled'
  count: number
  items: LedgerEntry[]
}

export async function getLedger(id: number) {
  return api<LedgerSummary>(`/partners/${id}/ledger`)
}
export async function recordLedgerEntry(
  id: number,
  body: { kind: LedgerKind; amount: number; direction?: number; note?: string },
) {
  return api<{ entry: LedgerEntry } & LedgerSummary>(`/partners/${id}/ledger`, {
    method: 'POST',
    body,
  })
}
