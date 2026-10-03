/** Tiny impersonation store, localStorage-backed with a change event so the
 *  persistent banner re-renders anywhere in the app. */

const KEY = 'wm.impersonation'
const EVENT = 'wm:impersonation'

export interface ImpersonationState {
  grant_id: number
  acting_as_user_id: number
  admin_token: string
  started_at: number
}

export function getImpersonation(): ImpersonationState | null {
  try {
    const raw = localStorage.getItem(KEY)
    return raw ? (JSON.parse(raw) as ImpersonationState) : null
  } catch {
    return null
  }
}

export function setImpersonation(state: ImpersonationState): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(state))
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new Event(EVENT))
}

export function clearImpersonation(): void {
  try {
    localStorage.removeItem(KEY)
  } catch {
    /* ignore */
  }
  window.dispatchEvent(new Event(EVENT))
}

export function onImpersonationChange(cb: () => void): () => void {
  window.addEventListener(EVENT, cb)
  return () => window.removeEventListener(EVENT, cb)
}
