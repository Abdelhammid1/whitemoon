import { api, downloadFile, openDocument } from './client'

// ---------------------------------------------------------------- catalog

export interface CatalogProduct {
  product_id: number
  sku: string
  name_ar: string
  category: string
  unit: string
  image_url: string | null
  best_price: string
  best_offer_id: number
}

export async function browseCatalog(params: { q?: string; category?: string } = {}) {
  return api<{ items: CatalogProduct[] }>('/catalog/products', { query: params })
}

export async function relatedProducts(productId: number) {
  return api<{ items: CatalogProduct[] }>(`/catalog/products/${productId}/related`)
}

// T-43 quick order: typo-tolerant search + filters.
export interface QuickSearchItem {
  product_id: number
  sku: string
  name_ar: string
  category: string
  brand: string | null
  barcode: string | null
  unit: string
  image_url: string | null
  best_price: string
  best_offer_id: number
  moq: string
  available: string
}
export interface QuickSearchParams {
  q?: string
  category?: string
  brand?: string
  price_min?: string
  price_max?: string
  in_stock?: string
  sort?: 'relevance' | 'price_asc' | 'price_desc' | 'name'
  limit?: string
}
export async function quickSearch(params: QuickSearchParams) {
  return api<{ items: QuickSearchItem[] }>('/catalog/quick-search', {
    query: params as Record<string, string | undefined>,
  })
}
export interface FilterOptions {
  brands: string[]
  categories: { code: string; name_ar: string }[]
}
export async function catalogFilterOptions() {
  return api<FilterOptions>('/catalog/filter-options')
}

export interface ProductDetail extends CatalogProduct {
  subcategory: string | null
  brand: string | null
  description: string | null
}
export async function getProduct(productId: number) {
  return api<ProductDetail>(`/catalog/products/${productId}`)
}

// ---------------------------------------------------------------- cart

export interface CartItem {
  item_id: number
  product_id: number
  name_ar: string | null
  qty: string
  locked_unit_price: string
  line_total: string
  price_locked_until: string | null
}
export interface Cart {
  cart_id: number
  status: string
  items: CartItem[]
  total: string
}

export async function getCart() {
  return api<Cart>('/commerce/cart')
}
export async function addCartItem(offer_id: number, qty: string) {
  return api<Cart>('/commerce/cart/items', { method: 'POST', body: { offer_id, qty } })
}
export async function updateCartItem(item_id: number, qty: string) {
  return api<Cart>(`/commerce/cart/items/${item_id}`, { method: 'PATCH', body: { qty } })
}
export async function removeCartItem(item_id: number) {
  return api<Cart>(`/commerce/cart/items/${item_id}`, { method: 'DELETE' })
}
export async function clearCart() {
  return api<Cart>('/commerce/cart/items', { method: 'DELETE' })
}

// ---------------------------------------------------------------- orders

export interface OrderLine {
  product_id: number
  qty: string
  unit_price: string
  line_total: string
}
/** Order source (T-33): company-direct, or an agent/branch by name. */
export interface OrderSource {
  type: 'company' | 'agent' | 'branch'
  user_id: number | null
  name: string
}
export interface Order {
  id: number
  number: string
  status: string
  payment_mode: string
  total_cash: string
  total_deferred: string
  placed_at: string
  source?: OrderSource
  lines?: OrderLine[]
  /** Customer view: each supplier part's status, no supplier identity (T-33). */
  parts?: { status: string; subtotal: string }[]
  /** Present on the admin/staff view instead of `lines`. */
  sub_orders?: AdminSubOrder[]
}

// ---------------------------------------------------------------- admin orders (T-13)

export type OrderStatus = 'pending' | 'confirmed' | 'fulfilled' | 'cancelled'
export type OrderAction = 'confirm' | 'fulfill' | 'cancel'

export interface AdminOrderLine {
  product_id: number
  supplier_offer_id: number
  qty: string
  unit_price: string
  line_total: string
}
export interface AdminSubOrder {
  id: number
  supplier_id: number
  status: string
  subtotal: string
  lines: AdminOrderLine[]
}
export interface AdminOrder {
  id: number
  number: string
  status: OrderStatus
  payment_mode: 'cash' | 'deferred'
  total_cash: string
  total_deferred: string
  placed_at: string
  customer_id: number
  customer_name: string | null
  source?: OrderSource
  sub_orders: AdminSubOrder[]
}

export async function adminListOrders(
  params: {
    status?: string
    customer_id?: string
    q?: string
    date_from?: string
    date_to?: string
    limit?: number
  } = {},
) {
  return api<{ items: AdminOrder[] }>('/commerce/admin/orders', { query: params })
}

/** Move an order through its lifecycle. An invalid transition returns 409. */
export async function transitionOrder(id: number, action: OrderAction) {
  return api<AdminOrder>(`/commerce/orders/${id}/${action}`, { method: 'POST' })
}
export const confirmOrder = (id: number) => transitionOrder(id, 'confirm')
export const fulfillOrder = (id: number) => transitionOrder(id, 'fulfill')
export const cancelOrder = (id: number) => transitionOrder(id, 'cancel')

export async function checkout(payment_mode: 'cash' | 'deferred', deferred_days?: number) {
  return api<Order>('/commerce/checkout', {
    method: 'POST',
    body: { payment_mode, ...(deferred_days != null ? { deferred_days } : {}) },
  })
}
export async function listOrders() {
  return api<{ items: Order[] }>('/commerce/orders')
}
export async function getOrder(id: number) {
  return api<Order>(`/commerce/orders/${id}`)
}

// ---------------------------------------------------------------- reorder / usual (T-42, T-32)
export interface ReorderWarning {
  product_id: number
  reason: 'price_changed' | 'unavailable' | 'already_in_cart' | 'could_not_add'
  old_price?: string
  new_price?: string
}
export async function reorder(orderId: number) {
  return api<{ added: number; warnings: ReorderWarning[] }>(`/commerce/orders/${orderId}/reorder`, { method: 'POST' })
}
export interface UsualItem {
  product_id: number
  name_ar: string
  image_url: string | null
  best_price: string
  best_offer_id: number
  usual_qty: string
}
export async function getUsualItems() {
  return api<{ items: UsualItem[] }>('/commerce/usual-items')
}
export interface UsualCategory {
  category: string
  count: number
  fallback: boolean
}
export async function getUsualCategories() {
  return api<{ items: UsualCategory[] }>('/commerce/usual-categories')
}

// ---------------------------------------------------------------- supplier home (T-41)
export interface SupplierSummary {
  new_orders: { sub_order_id: number; order_number: string; status: string; subtotal: string; placed_at: string }[]
  low_stock: { product_id: number; name: string; on_hand: string; reorder_point: string | null }[]
  expiring_discounts: { product_id: number; name: string; discount_end: string | null }[]
  counts: { new_orders: number; low_stock: number; expiring_discounts: number }
}
export async function getSupplierSummary() {
  return api<SupplierSummary>('/commerce/supplier/summary')
}
export async function advanceSubOrder(subOrderId: number, action: 'confirm' | 'ready') {
  return api<{ sub_order_id: number; status: string }>(`/commerce/supplier/sub-orders/${subOrderId}/${action}`, { method: 'POST' })
}

// ---------------------------------------------------------------- RFQ

export interface Rfq {
  id: number
  number: string
  product_id: number
  product_name?: string | null
  qty: string
  deadline: string | null
  qualification_requirements: string | null
  status: string
  offer_count: number
  my_offer?: { unit_price: string; moq: string }
}
export interface RfqOffer {
  offer_id: number
  unit_price: string
  moq: string
  submitted_at: string
  supplier_id?: number // admin-only; never present for a customer
}

export async function listRfqs() {
  return api<{ items: Rfq[] }>('/commerce/rfqs')
}

export async function createRfq(body: {
  product_id: number
  qty: string
  deadline?: string
  qualification_requirements?: string
}) {
  return api<Rfq>('/commerce/rfqs', { method: 'POST', body })
}
export async function getRfq(id: number) {
  return api<Rfq>(`/commerce/rfqs/${id}`)
}
export async function listRfqOffers(id: number) {
  return api<{ items: RfqOffer[] }>(`/commerce/rfqs/${id}/offers`)
}
export async function submitRfqOffer(id: number, unit_price: string, moq: string) {
  return api<{ offer_id: number }>(`/commerce/rfqs/${id}/offers`, {
    method: 'POST',
    body: { unit_price, moq },
  })
}

export interface SupplierOrderRow {
  sub_order_id: number
  order_number: string
  order_status: string
  sub_order_status: string
  subtotal?: string
  lines?: { product_id: number; qty: string; line_total: string }[]
}
export async function supplierOrders() {
  return api<{ items: SupplierOrderRow[] }>('/commerce/supplier/orders')
}

export interface CustomerStatement {
  customer_id: number
  profile: { display_name: string | null; geo_area: string | null }
  tier: string
  credit_limit: string
  outstanding: string
  available: string
  /** Date the balance figures are current as of (YYYY-MM-DD). */
  as_of?: string
  orders: Order[]
  dues: { id: number; amount: string; due_date: string; status: string; days_late: number | null }[]
  payments: { id: number; amount: string; paid_on: string; source: string }[]
}
export async function customerStatement(customerId: number, range: { from?: string; to?: string } = {}) {
  return api<CustomerStatement>(`/commerce/customers/${customerId}/statement`, { query: range })
}
/** Open the Arabic PDF (or printable HTML) statement in a new tab. */
export async function openStatementPdf(customerId: number, range: { from?: string; to?: string } = {}) {
  return openDocument(`/commerce/customers/${customerId}/statement.pdf`, range)
}
/** Download the .xlsx statement. */
export async function downloadStatementXlsx(customerId: number, range: { from?: string; to?: string } = {}) {
  return downloadFile(`/commerce/customers/${customerId}/statement.xlsx`, `statement-${customerId}.xlsx`, range)
}
/** Open the Arabic PDF (or printable HTML) invoice for an order in a new tab. */
export async function openOrderInvoice(orderId: number) {
  return openDocument(`/commerce/orders/${orderId}/invoice`)
}
