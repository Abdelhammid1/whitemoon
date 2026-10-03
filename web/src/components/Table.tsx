import type { ReactNode } from 'react'

interface Column<Row> {
  header: ReactNode
  cell: (row: Row) => ReactNode
  align?: 'start' | 'center' | 'end'
  width?: string
}

interface Props<Row> {
  columns: Column<Row>[]
  rows: Row[]
  rowKey: (row: Row) => string | number
  empty?: ReactNode
}

/**
 * Flat table. Hairline Warm-Mist row borders, Soft-Paper header. No
 * stripes, no shadows beyond the containing card.
 */
export function Table<Row>({ columns, rows, rowKey, empty }: Props<Row>) {
  if (rows.length === 0) {
    return (
      <div className="rounded-xl border border-warm-mist bg-soft-paper px-4 py-6 text-body text-graphite">
        {empty ?? 'لا توجد بيانات بعد.'}
      </div>
    )
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-warm-mist">
      <table className="min-w-full text-body">
        <thead className="bg-soft-paper">
          <tr>
            {columns.map((c, i) => (
              <th
                key={i}
                className={`px-3 py-2 text-${c.align ?? 'start'} text-body-sm text-graphite`}
                style={c.width ? { width: c.width } : undefined}
              >
                {c.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey(row)}
              className="border-t border-warm-mist text-ink hover:bg-soft-paper"
            >
              {columns.map((c, i) => (
                <td key={i} className={`px-3 py-2 text-${c.align ?? 'start'}`}>
                  {c.cell(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
