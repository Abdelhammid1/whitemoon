import { api } from './client'

export interface Dashboard {
  currency: string
  sales: {
    orders_by_status: Record<string, number>
    realized_revenue: string
    today: string
    open_orders: number
    weekly: { date: string; total: string }[]
  }
  collection: {
    dues_by_status: Record<string, number>
    outstanding: string
    defaulted: string
    overdue: string
  }
  credit: { tier_distribution: Record<string, number> }
  inventory: { low_stock_slots: number }
  pos: { unposted_total: string }
  logistics: { shipments_by_status: Record<string, number> }
  production: { orders_by_status: Record<string, number> }
  communication: { open_conversations: number; flagged_conversations: number }
}

export async function getDashboard() {
  return api<Dashboard>('/bi/dashboard')
}
