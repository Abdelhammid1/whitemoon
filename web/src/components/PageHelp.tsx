import { useState } from 'react'
import { Icon } from './Icon'
import { PAGE_HELP, type PageHelpContent } from '../content/pageHelp'

/**
 * Collapsible "عن هذه الصفحة" box (T-17). Sits directly under the page title on
 * every screen, for every role. The collapse choice is remembered per page,
 * per browser, via localStorage. Copy lives in one file: content/pageHelp.ts.
 */
export function PageHelp({ pageKey, content }: { pageKey?: string; content?: PageHelpContent }) {
  const data = content ?? (pageKey ? PAGE_HELP[pageKey] : undefined)
  const storageKey = `wm-help-${pageKey ?? 'inline'}`
  const [open, setOpen] = useState<boolean>(() => {
    try {
      const v = localStorage.getItem(storageKey)
      return v === null ? true : v === '1'
    } catch {
      return true
    }
  })

  if (!data) return null

  function toggle() {
    setOpen((o) => {
      const next = !o
      try {
        localStorage.setItem(storageKey, next ? '1' : '0')
      } catch {
        /* private mode / blocked storage — fine */
      }
      return next
    })
  }

  return (
    <div className="mt-space-md rounded-2xl border border-surface-container-high bg-surface-container-low overflow-hidden">
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-space-sm px-space-lg py-space-sm text-start transition-colors hover:bg-surface-container"
      >
        <span className="flex items-center gap-space-sm font-body-medium text-body-medium text-on-surface">
          <Icon name="help" size={18} className="text-primary" /> عن هذه الصفحة
        </span>
        <Icon name={open ? 'expand_less' : 'expand_more'} size={20} className="text-secondary" />
      </button>

      {open && (
        <div className="px-space-lg pb-space-lg pt-space-xs flex flex-col gap-space-sm font-body text-body text-on-surface-variant">
          <p>{data.purpose}</p>

          {data.steps.length > 0 && (
            <ol className="flex flex-col gap-space-xs ps-space-lg list-decimal marker:text-outline">
              {data.steps.map((s, i) => (
                <li key={i}>{s}</li>
              ))}
            </ol>
          )}

          {data.afterSave && (
            <p>
              <span className="font-body-medium text-on-surface">بعد الحفظ:</span> {data.afterSave}
            </p>
          )}

          {data.warning && (
            <p className="flex items-start gap-space-xs rounded-lg bg-warning-weak text-warning px-space-sm py-space-xs">
              <Icon name="warning" size={16} className="shrink-0 mt-0.5" />
              <span>{data.warning}</span>
            </p>
          )}
        </div>
      )}
    </div>
  )
}
