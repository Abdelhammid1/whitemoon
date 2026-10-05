import { api } from './client'

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

// ---------------------------------------------------------------- orders

export interface OrderLine {
  product_id: number
  qty: string
  unit_price: string
  line_total: string
}
export interface Order {
  id: number
  number: string
  status: string
  payment_mode: string
  total_cash: string
  total_deferred: string
  placed_at: string
  lines?: OrderLine[]
}

export async function checkout(payment_mode: 'cash' | 'deferred') {
  return api<Order>('/commerce/checkout', { method: 'POST', body: { payment_mode } })
}
export async function listOrders() {
  return api<{ items: Order[] }>('/commerce/orders')
}
export async function getOrder(id: number) {
  return api<Order>(`/commerce/orders/${id}`)
}

// ---------------------------------------------------------------- RFQ

export interface Rfq {
  id: number
  number: string
  product_id: number
  qty: string
  deadline: string | null
  qualification_requirements: string | null
  status: string
  offer_count: number
}
export interface RfqOffer {
  offer_id: number
  unit_price: string
  moq: string
  submitted_at: string
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
