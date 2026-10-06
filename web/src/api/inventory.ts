import { api, API_BASE, ApiError, tokenStore } from './client'

export type ProductStatus = 'active' | 'draft' | 'suspended'
export type EtaCodeType = 'EGS' | 'GS1'

export interface ProductVariant {
  id: number
  sku: string
  barcode: string | null
  size: string | null
  color: string | null
  pack: string | null
  is_active: boolean
}
export interface ProductImage {
  id: number
  url: string
  is_primary: boolean
  sort_order?: number
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
  eta_code_type?: EtaCodeType | null
  eta_ready?: boolean
  tax_rate?: string | null
  food_expiry_tracked: boolean
  status?: ProductStatus
  is_active: boolean
  wholesale_price?: string | null
  deferred_price?: string | null
  default_moq?: string | null
  variants?: ProductVariant[]
  images?: ProductImage[]
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
/** Variant payload accepted by create/update (replaces the variant set wholesale). */
export interface ProductVariantInput {
  sku: string
  barcode?: string
  size?: string
  color?: string
  pack?: string
}
/** Image payload accepted by create/update for external URLs (max 5). */
export interface ProductImageInput {
  url: string
  is_primary?: boolean
}
/** Optional opening stock batch created alongside the product. */
export interface InitialBatchInput {
  supplier_id: number
  batch_code: string
  production_date: string // YYYY-MM-DD
  expiry_date: string // YYYY-MM-DD
  qty: string
}
/** Full rich create/update body (every field optional on update). */
export interface ProductInput {
  sku?: string
  name_ar?: string
  category?: string
  name_en?: string
  unit?: string
  description?: string
  brand?: string
  barcode?: string
  subcategory?: string
  status?: ProductStatus
  eta_code?: string
  eta_code_type?: EtaCodeType
  tax_rate?: string
  food_expiry_tracked?: boolean
  wholesale_price?: string
  deferred_price?: string
  default_moq?: string
  image_url?: string
  variants?: ProductVariantInput[]
  images?: ProductImageInput[]
  initial_batch?: InitialBatchInput
}

export async function createProduct(body: ProductInput) {
  return api<Product>('/inventory/products', { method: 'POST', body })
}
export async function updateProduct(id: number, body: ProductInput) {
  return api<Product>(`/inventory/products/${id}`, { method: 'PUT', body })
}
export async function getProductDetail(id: number) {
  return api<Product>(`/inventory/products/${id}`)
}
/** Attach an image to a product: a File is uploaded as multipart; a string is
 *  attached as an external URL (JSON). Returns the stored image record. */
export async function uploadProductImage(
  id: number,
  fileOrUrl: File | string,
  isPrimary = false,
): Promise<ProductImage> {
  if (typeof fileOrUrl === 'string') {
    return api<ProductImage>(`/inventory/products/${id}/images`, {
      method: 'POST',
      body: { url: fileOrUrl, is_primary: isPrimary },
    })
  }
  const form = new FormData()
  form.append('image', fileOrUrl)
  if (isPrimary) form.append('is_primary', 'true')
  const headers: Record<string, string> = { Accept: 'application/json' }
  const token = tokenStore.getAccess()
  if (token) headers.Authorization = `Bearer ${token}`
  const resp = await fetch(`${API_BASE}/inventory/products/${id}/images`, {
    method: 'POST',
    headers,
    body: form,
  })
  const data = await resp.json().catch(() => null)
  if (!resp.ok) {
    throw new ApiError(resp.status, data?.error ?? 'error', data?.message ?? 'تعذّر رفع الصورة')
  }
  return data as ProductImage
}
/** Remove one product image (T-14 edit). */
export async function deleteProductImage(productId: number, imageId: number) {
  return api<{ deleted: number }>(`/inventory/products/${productId}/images/${imageId}`, { method: 'DELETE' })
}
/** Make an existing image the primary one (mirrored to the catalog). */
export async function setPrimaryProductImage(productId: number, imageId: number) {
  return api<{ primary: number }>(`/inventory/products/${productId}/images/${imageId}/primary`, { method: 'POST' })
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
  return api<{ created: ReorderAlert[] }>('/inventory/reorder/check', {
    method: 'POST',
    query: supplierId ? { supplier_id: supplierId } : {},
  })
}
export interface ReorderAlert {
  id: number
  stock_balance_id: number
  level: number
  payload: Record<string, unknown>
  acknowledged_at: string | null
}
export async function reorderAlerts(openOnly = true) {
  return api<{ items: ReorderAlert[] }>('/inventory/reorder/alerts', {
    query: { open: openOnly ? 'true' : 'false' },
  })
}
export async function reorderEscalate() {
  return api<{ advanced: number; closed: number }>('/inventory/reorder/escalate', { method: 'POST' })
}
export async function ackReorderAlert(id: number) {
  return api<ReorderAlert>(`/inventory/reorder/alerts/${id}/ack`, { method: 'POST' })
}
export async function reportShortage(body: {
  product_id: number
  supplier_id: number
  qty: number
  unit_cost: number
  evidence_s3_keys: string[] // US-4.4: photo documentation is mandatory
  transfer_order_id?: number
}) {
  return api<Shortage>('/inventory/shortages', { method: 'POST', body })
}
export interface Category {
  code: string
  label: string
  name_ar?: string
  name_en?: string | null
  icon?: string | null
  image_url?: string | null
  parent_code?: string | null
  sort_order?: number
  is_active?: boolean
}
export async function listCategories() {
  return api<{ items: Category[] }>('/inventory/categories')
}
// --- T-15: admin category management ---
export interface ManagedCategory extends Category {
  name_ar: string
  parent_code: string | null
  sort_order: number
  is_active: boolean
  product_count: number
}
export async function listCategoriesManage() {
  return api<{ items: ManagedCategory[] }>('/inventory/categories/manage')
}
export async function createCategory(body: {
  name_ar: string
  code?: string
  name_en?: string
  icon?: string
  image_url?: string
  parent_code?: string
  sort_order?: number
}) {
  return api<ManagedCategory>('/inventory/categories', { method: 'POST', body })
}
export async function updateCategory(
  code: string,
  body: Partial<{
    name_ar: string
    name_en: string
    icon: string
    image_url: string
    parent_code: string
    sort_order: number
    is_active: boolean
  }>,
) {
  return api<ManagedCategory>(`/inventory/categories/${code}`, { method: 'PUT', body })
}
export async function deleteCategory(code: string) {
  return api<{ deleted: string }>(`/inventory/categories/${code}`, { method: 'DELETE' })
}
/** Stock/transfer location types (code + Arabic label) from the backend. */
export async function listLocationTypes() {
  return api<{ items: Category[] }>('/inventory/location-types')
}

// --- planned read endpoints (not built yet; return [] on 404) ---

export async function listTransfersPlanned() {
  return api<{ items: TransferOrder[] }>('/inventory/transfers')
}
