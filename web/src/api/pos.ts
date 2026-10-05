import { api } from './client'

export interface PosLine {
  product_id: number
  category: string
  qty: string
  unit_price: string
  line_total: string
}
export interface PosSale {
  id: number
  number: string
  cashier_id: number
  location_type: string
  location_id: number | null
  total: string
  status: string
  posted: boolean
  batch_id: number | null
  lines: PosLine[]
}
export interface PosBatch {
  id: number
  posted_by: number
  posted_at: string
  sale_count: number
  total: string
  journal_entry_id: number | null
}

export async function createSale(lines: { product_id: number; supplier_id: number; qty: number }[]) {
  return api<PosSale>('/pos/sales', { method: 'POST', body: { lines } })
}
export async function listSales(posted?: boolean) {
  return api<{ items: PosSale[] }>('/pos/sales', {
    query: posted === undefined ? undefined : { posted: String(posted) },
  })
}
export async function settleBatch() {
  return api<PosBatch>('/pos/settle', { method: 'POST', body: {} })
}

export async function getSale(id: number) {
  return api<PosSale>(`/pos/sales/${id}`)
}
