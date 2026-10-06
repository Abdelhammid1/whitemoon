import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { Narrow } from '../../layouts/AppShell'
import { PageTitle, Button, Field, Pill, Card, Spinner, InlineError, EmptyState } from '../../components/ui'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { useAuth } from '../../auth/AuthContext'
import {
  customerStatement,
  openStatementPdf,
  downloadStatementXlsx,
  type CustomerStatement,
} from '../../api/commerce'
import { ApiError } from '../../api/client'
import { formatMoney, formatNumber, formatDate } from '../../lib/format'

type Tone = 'signal' | 'warning' | 'error' | 'neutral'
const TIER_AR: Record<string, string> = { green: 'أخضر', white: 'أبيض', yellow: 'أصفر', red: 'أحمر' }
const TIER_TONE: Record<string, Tone> = { green: 'signal', white: 'neutral', yellow: 'warning', red: 'error' }

const DUE_STATUS_AR: Record<string, string> = {
  open: 'مفتوحة',
  paid: 'مسددة',
  defaulted: 'متعثرة',
  cancelled: 'ملغاة',
}
const DUE_STATUS_TONE: Record<string, Tone> = {
  open: 'warning',
  paid: 'signal',
  defaulted: 'error',
  cancelled: 'neutral',
}
const SOURCE_AR: Record<string, string> = { customer: 'تحويل مرفوع', collector: 'تحصيل ميداني' }

export function StatementPage() {
  const toast = useToast()
  const { user } = useAuth()
  const { id } = useParams()
  const customerId = id ? Number(id) : (user?.id ?? 0)

  const [data, setData] = useState<CustomerStatement | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [exporting, setExporting] = useState(false)

  // Draft filter inputs; `applied` is what actually drives the loaded data.
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [applied, setApplied] = useState<{ from?: string; to?: string }>({})

  const load = useCallback(
    async (range: { from?: string; to?: string }) => {
      if (!customerId) return
      setLoading(true)
      setError(null)
      try {
        setData(await customerStatement(customerId, range))
      } catch (err) {
        setError(err instanceof ApiError ? err.message : 'تعذّر تحميل كشف الحساب')
      } finally {
        setLoading(false)
      }
    },
    [customerId],
  )

  useEffect(() => {
    void load(applied)
  }, [load, applied])

  function applyFilter() {
    setApplied({ from: from || undefined, to: to || undefined })
  }
  function clearFilter() {
    setFrom('')
    setTo('')
    setApplied({})
  }

  async function exportAs(kind: 'pdf' | 'xlsx') {
    setExporting(true)
    try {
      if (kind === 'pdf') await openStatementPdf(customerId, applied)
      else await downloadStatementXlsx(customerId, applied)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر التصدير')
    } finally {
      setExporting(false)
    }
  }

  const tier = data?.tier ?? ''

  return (
    <Narrow>
      <div className="flex flex-wrap items-center justify-between gap-space-md">
        <PageTitle
          title="كشف الحساب"
          subtitle="الذمم والمدفوعات والرصيد والسقف المتاح"
        />
        <div className="flex items-center gap-space-sm">
          <Button onClick={() => exportAs('pdf')} disabled={exporting || !data} iconRight="picture_as_pdf">
            PDF
          </Button>
          <Button onClick={() => exportAs('xlsx')} disabled={exporting || !data} iconRight="download">
            Excel
          </Button>
        </div>
      </div>
      <PageHelp pageKey="statement" />

      {/* Date-range filter */}
      <Card className="mt-space-lg flex flex-wrap items-end gap-space-md">
        <div className="w-40">
          <Field label="من تاريخ" type="date" mono dir="ltr" value={from} onChange={(e) => setFrom(e.target.value)} />
        </div>
        <div className="w-40">
          <Field label="إلى تاريخ" type="date" mono dir="ltr" value={to} onChange={(e) => setTo(e.target.value)} />
        </div>
        <Button variant="primary" onClick={applyFilter} iconRight="filter_alt">
          تطبيق
        </Button>
        {(applied.from || applied.to) && (
          <Button onClick={clearFilter} iconRight="close">
            مسح الفلتر
          </Button>
        )}
      </Card>

      {loading ? (
        <div className="mt-space-xl">
          <Spinner />
        </div>
      ) : error ? (
        <div className="mt-space-xl">
          <InlineError message={error} />
        </div>
      ) : data ? (
        <div className="mt-space-xl flex flex-col gap-space-xl">
          {/* KPI summary — balance is the current position (as of today), even
              when a date range filters the tables below. */}
          <div className="flex flex-col gap-space-xs">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-space-md">
              <Kpi label="السقف الائتماني" value={formatMoney(data.credit_limit)} />
              <Kpi label="الرصيد المستحق" value={formatMoney(data.outstanding)} />
              <Kpi
                label="المتاح"
                value={formatMoney(data.available)}
                extra={
                  tier ? <Pill tone={TIER_TONE[tier] ?? 'neutral'}>{TIER_AR[tier] ?? tier}</Pill> : undefined
                }
              />
            </div>
            <p className="font-small text-small text-secondary">
              الرصيد والسقف محسوبان حتى تاريخه{data.as_of ? ` (${data.as_of})` : ''}، بصرف النظر عن فلتر الفترة.
            </p>
          </div>

          {/* Dues */}
          <Card padded={false}>
            <div className="px-space-lg pt-space-lg pb-space-sm font-headline-2 text-headline-2 text-primary">
              الذمم
            </div>
            {data.dues.length === 0 ? (
              <EmptyState title="لا توجد ذمم في هذه الفترة" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-start">
                  <thead>
                    <tr className="border-b border-surface-container-high text-secondary font-small text-small">
                      <th className="text-start py-space-sm px-space-lg">تاريخ الاستحقاق</th>
                      <th className="text-start py-space-sm px-space-lg">المبلغ</th>
                      <th className="text-start py-space-sm px-space-lg">الحالة</th>
                      <th className="text-start py-space-sm px-space-lg">أيام التأخير</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.dues.map((d) => (
                      <tr key={d.id} className="border-b border-surface-container-low last:border-0">
                        <td className="py-space-sm px-space-lg font-mono-body" dir="ltr">
                          {formatDate(d.due_date)}
                        </td>
                        <td className="py-space-sm px-space-lg">{formatMoney(d.amount)}</td>
                        <td className="py-space-sm px-space-lg">
                          <Pill tone={DUE_STATUS_TONE[d.status] ?? 'neutral'}>
                            {DUE_STATUS_AR[d.status] ?? d.status}
                          </Pill>
                        </td>
                        <td className="py-space-sm px-space-lg">
                          {d.days_late != null ? formatNumber(d.days_late) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          {/* Payments */}
          <Card padded={false}>
            <div className="px-space-lg pt-space-lg pb-space-sm font-headline-2 text-headline-2 text-primary">
              المدفوعات المعتمدة
            </div>
            {data.payments.length === 0 ? (
              <EmptyState title="لا توجد مدفوعات في هذه الفترة" />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-start">
                  <thead>
                    <tr className="border-b border-surface-container-high text-secondary font-small text-small">
                      <th className="text-start py-space-sm px-space-lg">التاريخ</th>
                      <th className="text-start py-space-sm px-space-lg">المبلغ</th>
                      <th className="text-start py-space-sm px-space-lg">المصدر</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.payments.map((p) => (
                      <tr key={p.id} className="border-b border-surface-container-low last:border-0">
                        <td className="py-space-sm px-space-lg font-mono-body" dir="ltr">
                          {formatDate(p.paid_on)}
                        </td>
                        <td className="py-space-sm px-space-lg">{formatMoney(p.amount)}</td>
                        <td className="py-space-sm px-space-lg">{SOURCE_AR[p.source] ?? p.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      ) : null}
    </Narrow>
  )
}

function Kpi({ label, value, extra }: { label: string; value: string; extra?: React.ReactNode }) {
  return (
    <Card className="flex flex-col gap-space-xs">
      <div className="flex items-center justify-between">
        <span className="font-small text-small text-secondary">{label}</span>
        {extra}
      </div>
      <span className="font-headline-1 text-headline-1 text-primary">{value}</span>
    </Card>
  )
}
