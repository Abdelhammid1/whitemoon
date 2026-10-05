import { api } from './client'

export interface ProductVariant {
  id: number
  sku: string
  barcode: string | null
  size: string | null
  color: string | null
  is_active: boolean
}
export interface Product {
  id: number
  sku: string
  name_ar: string
  name_en: string | null
  category: string
  subcategory?: string | null
  brand?: string | null
  barcode?: string | null
  description?: string | null
  image_url?: string | null
  unit: string
  eta_code: string | null
  food_expiry_tracked: boolean
  is_active: boolean
  variants?: ProductVariant[]
}

/** Allowed product categories (curated list, T-10) — code → Arabic label. */
export const PRODUCT_CATEGORIES: { code: string; label: string }[] = [
  { code: 'food', label: 'غذائية' },
  { code: 'clothing', label: 'ملابس' },
  { code: 'electronics', label: 'إلكترونيات' },
  { code: 'home', label: 'أدوات منزلية' },
  { code: 'beauty', label: 'عناية وتجميل' },
  { code: 'construction', label: 'مواد بناء' },
  { code: 'stationery', label: 'قرطاسية' },
  { code: 'automotive', label: 'قطع غيار' },
  { code: 'other', label: 'أخرى' },
]

export interface Offer {
  id: number
  product_id: number
  unit_price: string
  moq: string
  is_active: boolean
  currency: string
}

export interface StockBalance {
  id: number
  supplier_id: number
  product_id: number
  location_type: string
  location_id: number | null
  on_hand: string
  reserved: string
  available: string
  reorder_point: string | null
  low: boolean
}

export interface TransferOrder {
  id: number
  number: string
  supplier_id: number
  from_location_type: string
  from_location_id: number | null
  to_location_type: string
  to_location_id: number | null
  status: string
  issue_entry_id: number | null
  receive_entry_id: number | null
  lines: { product_id: number; qty: string; unit_cost: string }[]
}

export interface Shortage {
  id: number
  product_id: number
  supplier_id: number
  qty: string
  unit_cost: string
  status: string
  responsible_party_type: string | null
  responsible_party_id: number | null
  journal_entry_id: number | null
  transfer_order_id: number | null
}

export async function listProducts(params: { q?: string; category?: string }) {
  return api<{ items: Product[] }>('/inventory/products', { query: params })
}
export async function createProduct(body: {
  sku: string
  name_ar: string
  name_en?: string
  category: string
  subcategory?: string
  brand?: string
  barcode?: string
  description?: string
  image_url?: string
  unit?: string
  eta_code?: string
  food_expiry_tracked?: boolean
}) {
  return api<Product>('/inventory/products', { method: 'POST', body })
}
export async function addVariant(
  productId: number,
  body: { sku: string; barcode?: string; size?: string; color?: string },
) {
  return api<{ id: number; product_id: number; sku: string }>(
    `/inventory/products/${productId}/variants`,
    { method: 'POST', body },
  )
}
export async function bestPrice(productId: number) {
  return api<{ product_id: number; best: { best_price: string; moq: string } | null }>(
    `/inventory/products/${productId}/best-price`,
  )
}
export async function myOffers() {
  return api<{ items: Offer[] }>('/inventory/offers/mine')
}
export async function upsertOffer(body: {
  product_id: number
  unit_price: string
  moq?: string
  is_active?: boolean
}) {
  return api<Offer>('/inventory/offers', { method: 'POST', body })
}
export async function stockBalances(params: { supplier_id?: number; location_type?: string }) {
  return api<{ items: StockBalance[] }>('/inventory/stock-balances', { query: params })
}
export async function adjustStock(body: {
  supplier_id: number
  product_id: number
  location_type: string
  location_id?: number
  delta: string
  reorder_point?: string
}) {
  return api<StockBalance>('/inventory/stock/adjust', { method: 'POST', body })
}
export async function getTransfer(id: number) {
  return api<TransferOrder>(`/inventory/transfers/${id}`)
}
export async function createTransfer(body: {
  supplier_id: number
  from_location_type: string
  from_location_id?: number
  to_location_type: string
  to_location_id?: number
  lines: { product_id: number; qty: string; unit_cost: string }[]
}) {
  return api<TransferOrder>('/inventory/transfers', { method: 'POST', body })
}
export async function issueTransfer(id: number) {
  return api<TransferOrder>(`/inventory/transfers/${id}/issue`, { method: 'POST' })
}
export async function receiveTransfer(id: number) {
  return api<TransferOrder>(`/inventory/transfers/${id}/receive`, { method: 'POST' })
}
export async function listShortages(params: { status?: string }) {
  return api<{ items: Shortage[] }>('/inventory/shortages', { query: params })
}
export async function resolveShortage(
  id: number,
  body: { responsible_party_type: string; responsible_party_id?: number; reason: string },
) {
  return api<Shortage>(`/inventory/shortages/${id}/resolve`, { method: 'POST', body })
}
export async function reorderCheck(supplierId?: number) {
  return api<{ created: unknown[] }>('/inventory/reorder/check', {
    method: 'POST',
    query: supplierId ? { supplier_id: supplierId } : {},
  })
}

// --- planned read endpoints (not built yet; return [] on 404) ---

export async function listTransfersPlanned() {
  return api<{ items: TransferOrder[] }>('/inventory/transfers')
}
