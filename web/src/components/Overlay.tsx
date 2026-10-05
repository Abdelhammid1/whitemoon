import { useEffect, type ReactNode } from 'react'
import { Icon } from './Icon'

/** Centered modal (≤540px) per DESIGN.md. */
export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-space-lg modal-backdrop" onClick={onClose}>
      <div
        className="w-full max-w-[560px] max-h-[90vh] flex flex-col bg-surface-container-lowest rounded-2xl border border-surface-container-high overlay-shadow"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-space-md px-space-lg py-space-md border-b border-surface-container-high shrink-0">
          <h2 className="font-headline-2 text-headline-2 text-on-surface font-semibold">{title}</h2>
          <button
            onClick={onClose}
            aria-label="إغلاق"
            className="w-8 h-8 -me-space-xs rounded-lg flex items-center justify-center text-secondary hover:bg-surface-container-low hover:text-on-surface transition-colors"
          >
            <Icon name="close" size={20} />
          </button>
        </div>
        <div className="px-space-lg py-space-lg overflow-y-auto">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-space-sm px-space-lg py-space-md border-t border-surface-container-high shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  )
}

/** Slide-over sheet from the inline-end (left in RTL), 440px. */
export function SideSheet({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
}) {
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 modal-backdrop" onClick={onClose}>
      <div
        className="absolute inset-y-0 left-0 w-full max-w-[460px] bg-surface-container-lowest border-e border-surface-container-high overlay-shadow flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-space-md px-space-lg py-space-md border-b border-surface-container-high shrink-0">
          <h2 className="font-headline-2 text-headline-2 text-on-surface font-semibold">{title}</h2>
          <button
            onClick={onClose}
            aria-label="إغلاق"
            className="w-8 h-8 -me-space-xs rounded-lg flex items-center justify-center text-secondary hover:bg-surface-container-low hover:text-on-surface transition-colors"
          >
            <Icon name="close" size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-space-lg py-space-lg">{children}</div>
      </div>
    </div>
  )
}
