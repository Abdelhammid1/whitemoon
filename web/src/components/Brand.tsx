import logoUrl from '../assets/white-moon-logo.png'

interface Props {
  size?: number
  withWordmark?: boolean
}

/** White Moon crescent-town mark + bilingual wordmark. The mark is cream, so it
 *  sits in a navy tile to stay visible on every surface (light or dark). */
export function Brand({ size = 24, withWordmark = true }: Props) {
  const tile = size + 10
  return (
    <div className="flex items-center gap-space-sm">
      <span
        className="inline-flex shrink-0 items-center justify-center rounded-lg bg-primary shadow-card-sm"
        style={{ width: tile, height: tile }}
      >
        <img
          src={logoUrl}
          alt="White Moon"
          width={size}
          height={size}
          style={{ width: size, height: size, objectFit: 'contain' }}
        />
      </span>
      {withWordmark && (
        <span className="font-headline-2 text-headline-2 text-primary font-medium tracking-tight">
          وايت مون
        </span>
      )}
    </div>
  )
}
