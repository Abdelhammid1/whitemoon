import { api } from './client'

export interface Slot {
  id: number
  slot_date: string
  window: string
  capacity: number
  booked: number
  remaining: number
  is_active: boolean
}
export interface ShipmentLeg {
  seq: number
  carrier_type: string
  carrier_ref: string | null
  from_label: string | null
  to_label: string | null
  status: string
}
export interface Shipment {
  id: number
  order_id: number
  slot_id: number | null
  carrier_type: string
  status: string
  current_lat: string | null
  current_lng: string | null
  location_updated_at: string | null
  delivered_at: string | null
  confirmation_code?: string
  shortages: { product_id: number; qty: string; photo_url: string | null; note: string | null }[]
  legs: ShipmentLeg[]
}

export async function createSlot(slot_date: string, window: string, capacity: number) {
  return api<Slot>('/logistics/slots', { method: 'POST', body: { slot_date, window, capacity } })
}
export async function availableSlots(from: string, to: string) {
  return api<{ items: Slot[] }>('/logistics/slots', { query: { from, to } })
}
export async function bookSlot(order_id: number, slot_id: number, carrier_type = 'internal') {
  return api<Shipment>('/logistics/book', { method: 'POST', body: { order_id, slot_id, carrier_type } })
}
export async function trackShipment(orderId: number) {
  return api<Shipment>(`/logistics/orders/${orderId}/shipment`)
}
export async function setShipmentStatus(id: number, status: string) {
  return api<{ id: number; status: string }>(`/logistics/shipments/${id}/status`, { method: 'POST', body: { status } })
}
export async function addLeg(id: number, body: { carrier_type: string; carrier_ref?: string; from_label?: string; to_label?: string }) {
  return api<{ id: number; seq: number }>(`/logistics/shipments/${id}/legs`, { method: 'POST', body })
}
export async function confirmDelivery(id: number, body: { confirmation_code?: string; signature?: string }) {
  return api<Shipment>(`/logistics/shipments/${id}/confirm`, { method: 'POST', body })
}
