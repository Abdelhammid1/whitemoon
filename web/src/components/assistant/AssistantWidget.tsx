import { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Icon } from '../Icon'
import { useAuth } from '../../auth/AuthContext'
import { AssistantChat } from './AssistantChat'

const LS_KEY = 'wm-assistant-open'

/**
 * Floating admin-assistant dock (ticket §19). Rendered only for admins — this
 * is defence in depth; the route/mount and the backend permission also gate it.
 * The panel carries the admin's current route so the assistant knows the page.
 */
export function AssistantWidget() {
  const { user } = useAuth()
  const location = useLocation()
  const [open, setOpen] = useState<boolean>(() => {
    try {
      return localStorage.getItem(LS_KEY) === '1'
    } catch {
      return false
    }
  })

  if (user?.kind !== 'admin') return null

  function toggle(next: boolean) {
    setOpen(next)
    try {
      localStorage.setItem(LS_KEY, next ? '1' : '0')
    } catch {
      /* storage disabled — fine */
    }
  }

  return (
    <>
      {/* launcher */}
      {!open && (
        <button
          type="button"
          onClick={() => toggle(true)}
          className="fixed bottom-5 left-5 z-40 inline-flex items-center gap-space-sm rounded-pill bg-primary px-space-md py-space-sm text-on-primary shadow-overlay transition-transform hover:scale-[1.03]"
          title="مساعد المدير"
        >
          <Icon name="smart_toy" size={22} />
          <span className="hidden font-body-medium text-body-medium sm:inline">مساعد المدير</span>
        </button>
      )}

      {/* slide-over panel */}
      {open && (
        <div className="fixed bottom-5 left-5 z-40 flex h-[min(620px,calc(100vh-40px))] w-[min(380px,calc(100vw-40px))] flex-col overflow-hidden rounded-2xl border border-surface-container-high bg-surface-container-lowest shadow-overlay">
          <div className="flex shrink-0 items-center justify-between border-b border-surface-container-high px-space-md py-space-sm">
            <span className="inline-flex items-center gap-space-xs font-body-medium text-body-medium text-primary">
              <Icon name="smart_toy" size={18} /> مساعد المدير
            </span>
            <div className="flex items-center gap-space-xs">
              <Link to="/assistant" title="فتح في صفحة كاملة" className="grid h-8 w-8 place-items-center rounded-lg text-secondary hover:bg-surface-container-low">
                <Icon name="open_in_full" size={18} />
              </Link>
              <button
                type="button"
                onClick={() => toggle(false)}
                title="إغلاق"
                className="grid h-8 w-8 place-items-center rounded-lg text-secondary hover:bg-surface-container-low"
              >
                <Icon name="close" size={18} />
              </button>
            </div>
          </div>
          <div className="min-h-0 flex-1">
            <AssistantChat route={location.pathname} compact />
          </div>
        </div>
      )}
    </>
  )
}
