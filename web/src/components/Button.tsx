import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Variant = 'filled' | 'ghost' | 'link'

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  children: ReactNode
}

/**
 * Button variants from DESIGN.md:
 *  - filled : Ink background, Parchment text, 12px radius, 8/12 padding
 *  - ghost  : transparent, 1px Warm-Mist border, 6px radius, 8/12 padding
 *  - link   : transparent, Graphite text, no border, hover→Ink
 */
export function Button({
  variant = 'ghost',
  className = '',
  type = 'button',
  disabled,
  children,
  ...rest
}: Props) {
  const base =
    'inline-flex items-center justify-center text-body font-normal transition-colors disabled:cursor-not-allowed disabled:opacity-60'
  const styleMap: Record<Variant, string> = {
    filled:
      'bg-ink text-parchment hover:bg-pure-black rounded-xl px-3 py-2 min-h-9',
    ghost:
      'bg-transparent text-graphite hover:text-ink border border-warm-mist rounded-md px-3 py-2 min-h-9',
    link: 'bg-transparent text-graphite hover:text-ink px-1 py-1',
  }
  return (
    <button
      type={type}
      disabled={disabled}
      className={`${base} ${styleMap[variant]} ${className}`.trim()}
      {...rest}
    >
      {children}
    </button>
  )
}
