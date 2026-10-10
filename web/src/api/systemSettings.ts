import { api } from './client'

/** A tunable business constant (T-37) with its metadata + current value. */
export interface Setting {
  key: string
  group: string
  label: string
  description: string
  example: string
  value_type: 'int' | 'decimal'
  unit: string
  minimum: string | null
  maximum: string | null
  default: string
  value: string
  overridden: boolean
  source: string
}

/** One entry in a setting's change log. */
export interface Change {
  id: number
  old_value: string | null
  new_value: string
  changed_by_id: number | null
  changed_at: string
}

export async function listSystemSettings() {
  return api<{ items: Setting[] }>('/admin/system-settings')
}
export async function updateSystemSetting(key: string, value: string) {
  return api<Setting>(`/admin/system-settings/${key}`, { method: 'PATCH', body: { value } })
}
export async function systemSettingChanges(key: string) {
  return api<{ items: Change[] }>(`/admin/system-settings/${key}/changes`)
}
