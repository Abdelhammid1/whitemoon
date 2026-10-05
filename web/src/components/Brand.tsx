interface Props {
  size?: number
  withWordmark?: boolean
}

/** White Moon crescent mark + bilingual wordmark, inline (no external image). */
export function Brand({ size = 24, withWordmark = true }: Props) {
  return (
    <div className="flex items-center gap-space-sm">
      <svg
        width={size}
        height={size}
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden
        xmlns="http://www.w3.org/2000/svg"
      >
        <path
          d="M15.5 2a10 10 0 1 0 6.5 17.3A8 8 0 0 1 15.5 2Z"
          fill="currentColor"
          className="text-gold"
        />
      </svg>
      {withWordmark && (
        <span className="font-headline-2 text-headline-2 text-primary font-medium tracking-tight">
          وايت مون
        </span>
      )}
    </div>
  )
}
