import { api } from './client'

export interface MOStage { seq: number; name: string; status: string }
export interface MOMaterial { product_id: number; qty: string; unit_cost: string }
export interface ManufacturingOrder {
  id: number
  number: string
  owner_id: number
  output_product_id: number
  output_qty: string
  location_type: string
  location_id: number | null
  status: string
  total_material_cost: string
  journal_entry_id: number | null
  stages: MOStage[]
  materials: MOMaterial[]
}

export async function listMOs(ownerId?: number) {
  return api<{ items: ManufacturingOrder[] }>('/production/orders', { query: ownerId ? { owner_id: ownerId } : undefined })
}
export async function getMO(id: number) {
  return api<ManufacturingOrder>(`/production/orders/${id}`)
}
export async function createMO(body: {
  owner_id: number
  output_product_id: number
  output_qty: number
  materials: { product_id: number; qty: number; unit_cost: number }[]
  stages: string[]
}) {
  return api<ManufacturingOrder>('/production/orders', { method: 'POST', body })
}
export async function advanceMO(id: number) {
  return api<{ mo_id: number; stage_seq: number; stage_status: string }>(`/production/orders/${id}/advance`, { method: 'POST' })
}
export async function completeMO(id: number) {
  return api<ManufacturingOrder>(`/production/orders/${id}/complete`, { method: 'POST', body: {} })
}
export async function cancelMO(id: number) {
  return api<{ id: number; status: string }>(`/production/orders/${id}/cancel`, { method: 'POST' })
}
