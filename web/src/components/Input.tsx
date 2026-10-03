import { forwardRef, type InputHTMLAttributes, type ReactNode } from 'react'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  hint?: ReactNode
  error?: string | null
}

/**
 * Input matches DESIGN.md: parchment bg, 12px radius, 1px Warm-Mist
 * border, 16px padding (compact 12px here to work in forms), Graphite
 * placeholder. Pure-black text focus ring (not teal) — teal is reserved.
 */
export const Input = forwardRef<HTMLInputElement, Props>(function Input(
  { label, hint, error, className = '', id, ...rest },
  ref,
) {
  const inputId = id ?? rest.name ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col gap-1">
      {label && (
        <label
          htmlFor={inputId}
          className="text-body-sm text-graphite"
        >
          {label}
        </label>
      )}
      <input
        ref={ref}
        id={inputId}
        className={`bg-parchment rounded-xl border border-warm-mist px-3 py-2 text-body text-ink placeholder:text-graphite outline-none focus:border-ink ${className}`}
        {...rest}
      />
      {error && <span className="text-caption text-ink">{error}</span>}
      {hint && !error && <span className="text-caption text-ash">{hint}</span>}
    </div>
  )
})
