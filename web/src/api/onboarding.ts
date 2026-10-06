import { api } from './client'

export interface OnboardingTask {
  key: string
  label: string
  /** Route to open for this task. */
  to: string
  /** 'auto' tasks are computed on the server; 'ack' tasks are acknowledged client-side. */
  done: boolean
  kind: 'auto' | 'ack'
}

export interface Onboarding {
  role: string | null
  tasks: OnboardingTask[]
  done_count: number
  total: number
}

export async function getChecklist() {
  return api<Onboarding>('/onboarding/checklist')
}
