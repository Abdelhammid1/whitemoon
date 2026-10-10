import { useCallback, useEffect, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { PageTitle, Button, Card, Spinner, InlineError, EmptyState } from '../../components/ui'
import { DataTable, Mono } from '../../components/DataTable'
import { Icon } from '../../components/Icon'
import { Modal } from '../../components/Overlay'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import { listDevices, revokeDevice, revokeAllDevices, type Device } from '../../api/auth'
import { ApiError } from '../../api/client'
import { formatDateTime } from '../../lib/format'

/** Friendly label from a raw User-Agent — OS · browser, best-effort. */
function parseUA(ua: string | null): string {
  if (!ua) return 'جهاز غير معروف'
  const os =
    /iPhone|iPad|iPod/i.test(ua) ? (/iPad/i.test(ua) ? 'iPad' : 'iPhone')
    : /Android/i.test(ua) ? 'Android'
    : /Windows/i.test(ua) ? 'Windows'
    : /Mac OS X|Macintosh/i.test(ua) ? 'macOS'
    : /Linux/i.test(ua) ? 'Linux'
    : null
  const browser =
    /Edg\//i.test(ua) ? 'Edge'
    : /OPR\/|Opera/i.test(ua) ? 'Opera'
    : /Chrome\//i.test(ua) ? 'Chrome'
    : /Firefox\//i.test(ua) ? 'Firefox'
    : /Safari\//i.test(ua) ? 'Safari'
    : null
  const label = [os, browser].filter(Boolean).join(' · ')
  return label || (ua.length > 40 ? `${ua.slice(0, 40)}…` : ua)
}

export function MyDevicesPage() {
  const toast = useToast()
  const [rows, setRows] = useState<Device[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [confirmAll, setConfirmAll] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try { setRows((await listDevices()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  async function revokeOne(id: number) {
    setBusy(true)
    try {
      await revokeDevice(id)
      toast.success('أُلغي الجهاز.')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الإلغاء')
    } finally { setBusy(false) }
  }

  async function revokeAll() {
    setBusy(true)
    try {
      const r = await revokeAllDevices()
      toast.success(`أُلغيت ${r.count} أجهزة.`)
      setConfirmAll(false)
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الإلغاء')
    } finally { setBusy(false) }
  }

  return (
    <Wide>
      <div className="flex flex-wrap items-start justify-between gap-space-sm">
        <PageTitle title="أجهزتي" subtitle="الأجهزة التي تدخل منها بدون كلمة مرور" />
        {rows.length > 0 && (
          <Button onClick={() => setConfirmAll(true)} disabled={busy} iconRight="logout">إلغاء الكل</Button>
        )}
      </div>

      <PageHelp pageKey="my-devices" />

      <div className="mt-space-md rounded-xl bg-surface-container-low px-space-md py-space-sm flex items-start gap-space-sm font-small text-small text-secondary">
        <Icon name="info" size={16} className="text-primary shrink-0 mt-0.5" />
        <span>هذه الأجهزة التي تدخل منها بدون كلمة مرور. ألغِ أي جهاز لا تعرفه أو لم تعد تستخدمه.</span>
      </div>

      <Card padded={false} className="mt-space-lg overflow-hidden">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : rows.length === 0 ? (
          <EmptyState title="لا توجد أجهزة متذكَّرة على حسابك." description="فعّل «تذكرني على هذا الجهاز» عند الدخول ليظهر الجهاز هنا." />
        ) : (
          <DataTable
            rows={rows}
            rowKey={(d) => d.id}
            columns={[
              { header: 'الجهاز', cell: (d) => <span className="font-body-medium text-body-medium text-primary">{parseUA(d.device)}</span> },
              { header: 'IP', cell: (d) => <Mono>{d.ip ?? '—'}</Mono> },
              { header: 'آخر استخدام', align: 'end', cell: (d) => <Mono>{formatDateTime(d.last_used_at ?? d.issued_at)}</Mono> },
              { header: 'أُضيف', align: 'end', cell: (d) => <Mono>{formatDateTime(d.issued_at)}</Mono> },
              {
                header: '', align: 'end',
                cell: (d) => (
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-small-medium text-small-medium text-secondary hover:text-error hover:bg-error/5 transition-colors disabled:opacity-40"
                    onClick={() => void revokeOne(d.id)}
                    disabled={busy}
                  >
                    <Icon name="link_off" size={16} />
                    <span>إلغاء</span>
                  </button>
                ),
              },
            ]}
          />
        )}
      </Card>

      <Modal
        open={confirmAll}
        onClose={() => setConfirmAll(false)}
        title="إلغاء كل الأجهزة"
        footer={
          <>
            <Button onClick={() => setConfirmAll(false)}>تراجع</Button>
            <Button variant="primary" onClick={() => void revokeAll()} disabled={busy}>نعم، ألغِ الكل</Button>
          </>
        }
      >
        <p className="font-body text-body text-secondary">
          سيُطلب تسجيل الدخول من جديد على كل الأجهزة المتذكَّرة (بما فيها هذا الجهاز). متابعة؟
        </p>
      </Modal>
    </Wide>
  )
}
