import { api } from './client'

export interface EtaReadiness {
  total_products: number
  eta_ready: number
  not_ready: number
  missing_eta_code: number[]
  currency: string
}
export interface ProductEta {
  product_id: number
  sku: string
  eta_code: string | null
  eta_ready: boolean
}

export async function etaReadiness() {
  return api<EtaReadiness>('/compliance/eta-readiness')
}
export async function setProductEta(productId: number, eta_code: string | null, eta_ready: boolean) {
  return api<ProductEta>(`/compliance/products/${productId}/eta`, {
    method: 'PUT',
    body: { eta_code, eta_ready },
  })
}
