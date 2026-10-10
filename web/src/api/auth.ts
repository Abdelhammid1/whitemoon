import { api, tokenStore } from './client'

export interface Me {
  id: number
  kind: 'customer' | 'supplier' | 'agent' | 'branch' | 'staff' | 'admin'
  status: 'pending' | 'active' | 'suspended' | 'locked'
  phone: string | null
  email: string | null
  locale: 'ar' | 'en'
  permissions: string[]
}

export interface RegisterCustomerBody {
  phone?: string
  email?: string
  password: string
  display_name: string
}

export interface RegisterSupplierBody {
  phone?: string
  email?: string
  password: string
  legal_name: string
  commercial_register_no: string
  tax_card_no: string
  national_id: string
}

export interface RegisterResponse {
  user_id: number
  status: string
  otp: { channel: string; expires_at: string; debug_code: string | null }
}

export interface LoginBody {
  phone?: string
  email?: string
  password: string
  totp_code?: string
}

export interface LoginResponse {
  user_id: number
  requires_2fa: boolean
  access_token?: string
  refresh_token?: string
}

export async function registerCustomer(body: RegisterCustomerBody) {
  return api<RegisterResponse>('/auth/register/customer', {
    method: 'POST',
    body,
    anonymous: true,
  })
}

export async function registerSupplier(body: RegisterSupplierBody) {
  return api<RegisterResponse>('/auth/register/supplier', {
    method: 'POST',
    body,
    anonymous: true,
  })
}

export async function verifyOtp(user_id: number, code: string) {
  return api<{ user_id: number; status: string; kind: string }>('/auth/otp/verify', {
    method: 'POST',
    body: { user_id, code },
    anonymous: true,
  })
}

export async function login(body: LoginBody): Promise<LoginResponse> {
  const resp = await api<LoginResponse>('/auth/login', {
    method: 'POST',
    body,
    anonymous: true,
  })
  if (!resp.requires_2fa && resp.access_token && resp.refresh_token) {
    tokenStore.setPair(resp.access_token, resp.refresh_token)
  }
  return resp
}

export async function me() {
  return api<Me>('/auth/me')
}

export async function logout() {
  try {
    await api('/auth/logout', { method: 'POST' })
  } finally {
    tokenStore.clear()
  }
}

export interface TotpEnrollStart {
  secret: string
  otpauth_uri: string
  backup_codes: string[]
}

export async function totpEnrollStart() {
  return api<TotpEnrollStart>('/auth/2fa/enroll/start', { method: 'POST' })
}

export async function totpEnrollFinish(code: string) {
  return api<{ status: string }>('/auth/2fa/enroll/finish', {
    method: 'POST',
    body: { code },
  })
}

export async function changePassword(current_password: string, new_password: string) {
  return api<{ status: string }>('/auth/change-password', {
    method: 'POST',
    body: { current_password, new_password },
  })
}
