interface Props {
  name: string
  size?: number
  className?: string
}

/** Material Symbols Outlined glyph (loaded in index.html). */
export function Icon({ name, size = 18, className = '' }: Props) {
  return (
    <span
      className={`material-symbols-outlined ${className}`}
      style={{ fontSize: size }}
      aria-hidden
    >
      {name}
    </span>
  )
}
