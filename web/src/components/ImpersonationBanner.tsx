import { useEffect, useState } from 'react'
import { tokenStore } from '../api/client'
import { stopImpersonation } from '../api/admin'
import {
  clearImpersonation,
  getImpersonation,
  onImpersonationChange,
  type ImpersonationState,
} from '../auth/impersonation'
import { useAuth } from '../auth/AuthContext'

/** Pinned single-line banner shown on every page while impersonating. */
export function ImpersonationBanner() {
  const [state, setState] = useState<ImpersonationState | null>(getImpersonation())
  const { refresh } = useAuth()

  useEffect(() => onImpersonationChange(() => setState(getImpersonation())), [])

  if (!state) return null

  async function onEnd() {
    if (!state) return
    try {
      await stopImpersonation(state.grant_id)
    } catch {
      /* even if the server call fails, restore the admin session locally */
    }
    tokenStore.setAccess(state.admin_token)
    clearImpersonation()
    await refresh()
  }

  return (
    <div className="h-10 px-[32px] flex items-center justify-between border-b border-danger/30 bg-danger-weak">
      <span className="font-small-medium text-small-medium text-danger">
        ⚠ تعمل الآن بصفة المستخدم{' '}
        <bdi dir="ltr" className="font-mono-medium">
          #{state.acting_as_user_id}
        </bdi>{' '}
        — جلسة دعم مسجَّلة في سجل التدقيق
      </span>
      <button
        onClick={onEnd}
        className="font-small-medium text-small-medium text-danger hover:underline underline-offset-4"
      >
        إنهاء الجلسة والعودة ↗
      </button>
    </div>
  )
}
