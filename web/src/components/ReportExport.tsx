import { useState } from 'react'
import { Button } from './ui'
import { useToast } from './Toast'
import { downloadReport } from '../api/accounting'
import { ApiError } from '../api/client'

/** "تصدير Excel / PDF" buttons for an accounting report (US-3.5). */
export function ReportExport({
  path,
  name,
  method = 'POST',
  body,
  query,
  disabled,
}: {
  path: string
  name: string // base filename (no extension)
  method?: 'GET' | 'POST'
  body?: unknown
  query?: Record<string, string>
  disabled?: boolean
}) {
  const toast = useToast()
  const [busy, setBusy] = useState(false)

  async function go(format: 'xlsx' | 'pdf') {
    setBusy(true)
    try {
      await downloadReport({ path, method, body, query, format, filename: `${name}.${format}` })
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التصدير')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex items-center gap-space-sm">
      <Button disabled={disabled || busy} onClick={() => go('xlsx')} iconRight="download">Excel</Button>
      <Button disabled={disabled || busy} onClick={() => go('pdf')} iconRight="picture_as_pdf">PDF</Button>
    </div>
  )
}
