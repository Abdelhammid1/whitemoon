import type { ReactNode } from 'react'
import { useScrollEdges } from '../lib/useScrollEdges'

type Align = 'start' | 'end' | 'center'

export interface Column<Row> {
  header: ReactNode
  cell: (row: Row) => ReactNode
  align?: Align
  width?: string
}

interface Props<Row> {
  columns: Column<Row>[]
  rows: Row[]
  rowKey: (row: Row, index: number) => string | number
  onRowClick?: (row: Row) => void
  empty?: ReactNode
}

const ALIGN: Record<Align, string> = {
  start: 'text-start',
  end: 'text-end',
  center: 'text-center',
}

/**
 * Ledger-style table from the Stitch export: no outer border, header on
 * surface-container-low with a hairline bottom rule, rows divided by a
 * single hairline, no zebra striping.
 */
export function DataTable<Row>({ columns, rows, rowKey, onRowClick, empty }: Props<Row>) {
  // T-35: fade the edge a wide table is still scrollable toward, so it is
  // apparent there are more columns off-screen (common on phones).
  const { ref, before, after } = useScrollEdges<HTMLDivElement>('x')
  if (rows.length === 0) {
    return (
      <div className="py-space-xl text-center font-body text-body text-secondary">
        {empty ?? 'لا توجد بيانات.'}
      </div>
    )
  }
  return (
    <div className="relative w-full">
      {before && (
        <div className="pointer-events-none absolute inset-y-0 start-0 z-10 w-6 bg-gradient-to-l from-black/[0.06] to-transparent" />
      )}
      {after && (
        <div className="pointer-events-none absolute inset-y-0 end-0 z-10 w-6 bg-gradient-to-r from-black/[0.06] to-transparent" />
      )}
      <div ref={ref} className="w-full overflow-x-auto">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-surface-container-low border-b border-surface-container-high">
            {columns.map((c, i) => (
              <th
                key={i}
                className={`px-space-sm py-space-sm font-small text-small text-secondary ${ALIGN[c.align ?? 'start']}`}
                style={c.width ? { width: c.width } : undefined}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr
              key={rowKey(row, index)}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
              className={`border-b border-surface-container-high ${
                onRowClick ? 'cursor-pointer hover:bg-surface' : ''
              }`}
            >
              {columns.map((c, i) => (
                <td
                  key={i}
                  className={`px-space-sm py-space-md align-middle ${ALIGN[c.align ?? 'start']}`}
                >
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      </div>
    </div>
  )
}

/** Monospace money/number cell: LTR digits, end-aligned. */
export function Mono({ children, className = '' }: { children: ReactNode; className?: string }) {
  return (
    <bdi className={`font-mono-body text-mono-body text-on-surface ${className}`} dir="ltr">
      {children}
    </bdi>
  )
}
