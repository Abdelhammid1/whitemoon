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
        className="w-full max-w-[540px] bg-surface-container-lowest rounded-xl overlay-shadow"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-space-lg py-space-md border-b border-surface-container-high">
          <h2 className="font-headline-2 text-headline-2 text-primary font-medium">{title}</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <Icon name="close" size={20} />
          </button>
        </div>
        <div className="px-space-lg py-space-lg">{children}</div>
        {footer && (
          <div className="flex items-center justify-end gap-space-sm px-space-lg py-space-md border-t border-surface-container-high">
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
        className="absolute inset-y-0 left-0 w-full max-w-[440px] bg-surface-container-lowest overlay-shadow flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-space-lg py-space-md border-b border-surface-container-high">
          <h2 className="font-headline-2 text-headline-2 text-primary font-medium">{title}</h2>
          <button onClick={onClose} className="text-secondary hover:text-primary">
            <Icon name="close" size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-space-lg py-space-lg">{children}</div>
      </div>
    </div>
  )
}
