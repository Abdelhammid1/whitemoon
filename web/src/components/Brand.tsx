/**
 * White-Moon brand mark — a crescent cut from a disc.
 * Ink filled, monochrome, scalable. DESIGN.md says the sidebar mark is
 * 16px; use `size={16}` there. On the auth pages a 36–40px treatment
 * reads as an identifying anchor rather than a glyph placeholder.
 */
interface Props {
  size?: number
  withWordmark?: boolean
}

export function Brand({ size = 32, withWordmark = true }: Props) {
  return (
    <div className="inline-flex items-center gap-3">
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        aria-hidden
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M20.5 2a14 14 0 1 0 9.5 24 11 11 0 0 1-9.5-22Z"
          fill="currentColor"
          className="text-ink"
        />
      </svg>
      {withWordmark && (
        <span className="text-body-lg text-ink" style={{ letterSpacing: 0 }}>
          وايت مون
        </span>
      )}
    </div>
  )
}
