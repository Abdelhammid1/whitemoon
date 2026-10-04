import { API_BASE, ApiError, tokenStore, api } from './client'

export interface ReceiptFileResult {
  receipt_id: number
  status: string
  image_s3_key: string
  ocr_amount: string | null
  ocr_reference: string | null
}

/** Upload the actual receipt image (multipart) — the server stores it and
 *  runs OCR. The browser sets the multipart boundary, so we don't set
 *  Content-Type ourselves. */
export async function uploadReceiptFile(
  file: File,
  opts: { expectedAmount?: string; expectedReference?: string; stubAmount?: string; stubReference?: string } = {},
): Promise<ReceiptFileResult> {
  const form = new FormData()
  form.append('image', file)
  if (opts.expectedAmount) form.append('expected_amount', opts.expectedAmount)
  if (opts.expectedReference) form.append('expected_reference', opts.expectedReference)
  if (opts.stubAmount) form.append('ocr_stub_amount', opts.stubAmount)
  if (opts.stubReference) form.append('ocr_stub_reference', opts.stubReference)

  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = tokenStore.getAccess()
  if (token) headers.Authorization = `Bearer ${token}`

  const resp = await fetch(`${API_BASE}/accounting/receipts/file`, {
    method: 'POST',
    headers,
    body: form,
  })
  const data = await resp.json().catch(() => null)
  if (!resp.ok) {
    throw new ApiError(resp.status, data?.error ?? 'error', data?.message ?? 'تعذّر الرفع')
  }
  return data as ReceiptFileResult
}

export interface PeriodRow {
  id: number
  year?: number
  month?: number
  is_closed?: boolean
}

export interface ManualJournalLine {
  account_code: string
  debit: string
  credit: string
  partner_type?: string
  partner_id?: number
  description?: string
}

export interface ReportFilterBody {
  date_from: string
  date_to: string
  account_prefix?: string
  partner_type?: string
  partner_id?: number
}

// ---------------------------------------------------------------- read views

export interface AccountRow {
  code: string
  name_ar: string
  name_en: string
  type: string
  parent_code: string | null
  is_postable: boolean
  category: string | null
  eta_code: string | null
}
export async function listAccounts() {
  return api<{ items: AccountRow[] }>('/accounting/accounts')
}

export interface PeriodListRow {
  id: number
  year: number
  month: number
  starts_on: string
  ends_on: string
  is_closed: boolean
  closed_at: string | null
}
export async function listPeriods(year?: number) {
  return api<{ items: PeriodListRow[] }>('/accounting/periods', {
    query: year ? { year } : undefined,
  })
}

export interface ReceiptRow {
  id: number
  status: string
  ocr_amount: string | null
  ocr_reference: string | null
  matched_order_id: number | null
  manual_review_reason: string | null
  uploaded_at: string | null
}
export async function listReceipts(status?: string) {
  return api<{ items: ReceiptRow[] }>('/accounting/receipts', {
    query: status ? { status } : undefined,
  })
}

export interface DeferredTermRow {
  id: number
  order_id: number
  cash_price: string
  deferred_price: string
  early_settlement_discount: string
  early_settlement_before: string | null
  discount_applied: boolean
  settled_at: string | null
}
export async function listDeferredTerms() {
  return api<{ items: DeferredTermRow[] }>('/accounting/deferred-terms')
}

export async function periodEnsure(year: number, month: number) {
  return api<PeriodRow>('/accounting/periods/ensure', {
    method: 'POST',
    body: { year, month },
  })
}

export async function periodClose(year: number, month: number) {
  return api<PeriodRow>('/accounting/periods/close', {
    method: 'POST',
    body: { year, month },
  })
}

export async function periodReopen(year: number, month: number) {
  return api<PeriodRow>('/accounting/periods/reopen', {
    method: 'POST',
    body: { year, month },
  })
}

export async function postManualJournal(body: {
  entry_date: string
  description: string
  reason: string
  allow_closed_period: boolean
  lines: ManualJournalLine[]
}) {
  return api<{ entry_id: number; entry_no: string }>('/accounting/journal/manual', {
    method: 'POST',
    body,
  })
}

export async function uploadReceipt(body: {
  image_s3_key: string
  expected_amount?: string
  expected_reference?: string
  ocr_stub_amount?: string
  ocr_stub_reference?: string
}) {
  return api<{
    receipt_id: number
    status: string
    ocr_amount: string | null
    ocr_reference: string | null
  }>('/accounting/receipts/upload', {
    method: 'POST',
    body,
  })
}

export async function resolveReceipt(receiptId: number, status: 'matched' | 'rejected') {
  return api<{ receipt_id: number; status: string }>(
    `/accounting/receipts/${receiptId}/resolve`,
    { method: 'POST', body: { status } },
  )
}

export async function createDeferredTerms(body: {
  order_id: number
  cash_price: string
  deferred_price: string
  early_settlement_discount: string
  early_settlement_before?: string
}) {
  return api<{
    id: number
    order_id: number
    cash_price: string
    deferred_price: string
    early_settlement_discount: string
    early_settlement_before: string | null
  }>('/accounting/deferred-terms', { method: 'POST', body })
}

export async function applyEarlyDiscount(order_id: number, settled_on: string) {
  return api<{ id: number; discount_applied: boolean }>(
    '/accounting/deferred-terms/apply-early-discount',
    { method: 'POST', body: { order_id, settled_on } },
  )
}

// ---------------------------------------------------------------- reports

export interface TrialBalanceRow {
  code: string
  name_ar: string
  name_en: string
  type: string
  debit: string
  credit: string
  balance: string
}
export interface TrialBalanceResponse {
  rows: TrialBalanceRow[]
  totals: { debit: string; credit: string; balanced: boolean }
}
export async function trialBalance(filter: ReportFilterBody) {
  return api<TrialBalanceResponse>('/accounting/reports/trial-balance', {
    method: 'POST',
    body: filter,
  })
}

export interface IncomeStatementResponse {
  revenues: { code: string; name_ar: string; amount: string }[]
  expenses: { code: string; name_ar: string; amount: string }[]
  totals: { revenue: string; expense: string; net_income: string }
}
export async function incomeStatement(filter: ReportFilterBody) {
  return api<IncomeStatementResponse>('/accounting/reports/income-statement', {
    method: 'POST',
    body: filter,
  })
}

export interface BalanceSheetResponse {
  as_of: string
  assets: { code: string; name_ar: string; amount: string }[]
  liabilities: { code: string; name_ar: string; amount: string }[]
  equity: { code: string; name_ar: string; amount: string }[]
  totals: { assets: string; liabilities: string; equity: string; balances: boolean }
}
export async function balanceSheet(filter: ReportFilterBody) {
  return api<BalanceSheetResponse>('/accounting/reports/balance-sheet', {
    method: 'POST',
    body: filter,
  })
}

export interface CashFlowResponse {
  sources: { code: string; name_ar: string; amount: string }[]
  uses: { code: string; name_ar: string; amount: string }[]
  net_cash_change: string
}
export async function cashFlow(filter: ReportFilterBody) {
  return api<CashFlowResponse>('/accounting/reports/cash-flow', {
    method: 'POST',
    body: filter,
  })
}

export interface GeneralLedgerRow {
  entry_no: string
  entry_date: string
  description: string
  debit: string
  credit: string
  running_balance: string
  partner_type: string | null
  partner_id: number | null
}
export interface GeneralLedgerResponse {
  account: { code: string; name_ar: string; type: string }
  date_from: string
  date_to: string
  rows: GeneralLedgerRow[]
  closing_balance: string
}
export async function generalLedger(
  account_code: string,
  date_from: string,
  date_to: string,
  limit = 500,
) {
  return api<GeneralLedgerResponse>(
    `/accounting/reports/general-ledger/${account_code}`,
    { query: { date_from, date_to, limit } },
  )
}
