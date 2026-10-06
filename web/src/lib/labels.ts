/**
 * Arabic labels for backend enum codes (T-16: no raw English status in the UI).
 * One place so every screen shows the same wording. `label(map, code)` falls
 * back to the raw code for an unknown value rather than throwing.
 */

export function label(map: Record<string, string>, code: string | null | undefined): string {
  if (!code) return '—'
  return map[code] ?? code
}

export const ORDER_STATUS_AR: Record<string, string> = {
  pending: 'قيد الانتظار',
  confirmed: 'مؤكَّد',
  preparing: 'قيد التجهيز',
  fulfilled: 'منفَّذ',
  cancelled: 'ملغى',
}

export const USER_STATUS_AR: Record<string, string> = {
  pending: 'قيد الاعتماد',
  active: 'مفعّل',
  suspended: 'مجمّد',
  locked: 'مغلق',
}

export const RECEIPT_STATUS_AR: Record<string, string> = {
  matched: 'مطابَق',
  unmatched: 'غير مطابَق',
  manual_review: 'مراجعة يدوية',
  pending: 'قيد الانتظار',
  rejected: 'مرفوض',
}

export const PAYMENT_SOURCE_AR: Record<string, string> = {
  customer: 'تحويل مرفوع',
  collector: 'تحصيل ميداني',
}

export const SHIPMENT_STATUS_AR: Record<string, string> = {
  scheduled: 'بالجدول',
  shipped: 'تم الشحن',
  in_transit: 'في الطريق',
  delivered: 'تم التسليم',
  failed: 'فشل',
}
