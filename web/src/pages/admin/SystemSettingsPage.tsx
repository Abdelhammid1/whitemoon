import { useEffect, useMemo, useState } from 'react'
import { Wide } from '../../layouts/AppShell'
import { Button, Card, Spinner, InlineError, Pill } from '../../components/ui'
import { Icon } from '../../components/Icon'
import { PageHelp } from '../../components/PageHelp'
import { useToast } from '../../components/Toast'
import {
  listSystemSettings,
  updateSystemSetting,
  systemSettingChanges,
  type Setting,
  type Change,
} from '../../api/systemSettings'
import { ApiError } from '../../api/client'
import { formatDateTime } from '../../lib/format'

export function SystemSettingsPage() {
  const [items, setItems] = useState<Setting[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try { setItems((await listSystemSettings()).items) }
    catch (err) { setError(err instanceof ApiError ? err.message : 'تعذّر التحميل') }
    finally { setLoading(false) }
  }
  useEffect(() => { void load() }, [])

  // Group by `.group`, preserving first-seen order.
  const groups = useMemo(() => {
    const out: { group: string; rows: Setting[] }[] = []
    const index = new Map<string, Setting[]>()
    for (const s of items) {
      let rows = index.get(s.group)
      if (!rows) {
        rows = []
        index.set(s.group, rows)
        out.push({ group: s.group, rows })
      }
      rows.push(s)
    }
    return out
  }, [items])

  function replaceRow(updated: Setting) {
    setItems((prev) => prev.map((s) => (s.key === updated.key ? updated : s)))
  }

  return (
    <Wide>
      <header className="flex flex-col">
        <div className="flex items-center gap-space-xs font-mono-body text-mono-body text-secondary mb-1" dir="ltr">
          <span>SYSTEM // SETTINGS</span>
        </div>
        <h1 className="font-display text-display text-primary font-medium tracking-tight">إعدادات النظام</h1>
      </header>

      <PageHelp pageKey="system-settings" />

      <div className="mt-space-md rounded-2xl border border-surface-container-high bg-surface-container-low px-space-lg py-space-md flex items-start gap-space-sm font-body text-body text-on-surface-variant">
        <Icon name="info" size={18} className="text-primary shrink-0 mt-0.5" />
        <span>هذه القيم تتحكم في سلوك النظام. كل قيمة مكتوب بجانبها ما تؤثر فيه. التغيير يُسجَّل.</span>
      </div>

      <div className="mt-space-xl flex flex-col gap-space-xl">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : (
          groups.map(({ group, rows }) => (
            <section key={group} className="flex flex-col gap-space-md">
              <h2 className="font-headline-1 text-headline-1 text-primary font-medium pb-space-sm border-b border-surface-container-highest">
                {group}
              </h2>
              <div className="flex flex-col gap-space-md">
                {rows.map((s) => (
                  <SettingRow key={s.key} setting={s} onSaved={replaceRow} />
                ))}
              </div>
            </section>
          ))
        )}
      </div>
    </Wide>
  )
}

function SettingRow({ setting, onSaved }: { setting: Setting; onSaved: (s: Setting) => void }) {
  const toast = useToast()
  const [draft, setDraft] = useState(setting.value)
  const [saving, setSaving] = useState(false)
  const [showLog, setShowLog] = useState(false)
  const [log, setLog] = useState<Change[] | null>(null)
  const [logLoading, setLogLoading] = useState(false)

  // Keep the input in sync when the row is replaced after a save.
  useEffect(() => { setDraft(setting.value) }, [setting.value])

  const dirty = draft.trim() !== setting.value && draft.trim() !== ''

  async function save() {
    setSaving(true)
    try {
      const updated = await updateSystemSetting(setting.key, draft.trim())
      onSaved(updated)
      setLog(null) // force a reload of the log next time it is opened
      toast.success(`حُفظت «${setting.label}».`)
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'تعذّر الحفظ')
    } finally {
      setSaving(false)
    }
  }

  async function toggleLog() {
    const next = !showLog
    setShowLog(next)
    if (next && log === null) {
      setLogLoading(true)
      try { setLog((await systemSettingChanges(setting.key)).items) }
      catch { setLog([]) }
      finally { setLogLoading(false) }
    }
  }

  const bounds =
    setting.minimum != null && setting.maximum != null
      ? `من ${setting.minimum} إلى ${setting.maximum}`
      : setting.minimum != null
        ? `الحد الأدنى ${setting.minimum}`
        : setting.maximum != null
          ? `الحد الأقصى ${setting.maximum}`
          : null

  return (
    <Card className="flex flex-col gap-space-sm">
      <div className="flex flex-wrap items-start justify-between gap-space-sm">
        <div className="flex flex-col gap-0.5 min-w-0">
          <span className="flex items-center gap-space-sm">
            <span className="font-body-medium text-body-medium text-primary">{setting.label}</span>
            {setting.overridden && <Pill tone="gold">معدّلة</Pill>}
          </span>
          <span className="font-body text-body text-secondary">{setting.description}</span>
          <span className="font-small text-small text-outline">{setting.example}</span>
        </div>
        <div className="flex items-end gap-space-sm shrink-0">
          <label className="flex flex-col">
            <span className="font-small text-small text-secondary mb-1">{setting.unit}</span>
            <input
              dir="ltr"
              type="number"
              step={setting.value_type === 'decimal' ? 'any' : '1'}
              min={setting.minimum ?? undefined}
              max={setting.maximum ?? undefined}
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              className="w-28 bg-transparent font-mono-body text-mono-body text-on-surface py-2 border-b border-surface-container-high focus:border-primary focus:border-b-2 focus:outline-none transition-all"
            />
          </label>
          <Button variant="primary" onClick={() => void save()} disabled={saving || !dirty}>حفظ</Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-space-md gap-y-1 font-small text-small text-outline">
        <span>الافتراضي: <bdi dir="ltr">{setting.default}</bdi></span>
        {bounds && <span>({bounds})</span>}
        <button type="button" onClick={() => void toggleLog()} className="inline-flex items-center gap-1 text-secondary hover:text-primary transition-colors">
          <Icon name={showLog ? 'expand_less' : 'history'} size={16} />
          <span>سجل التغيير</span>
        </button>
      </div>

      {showLog && (
        <div className="rounded-xl bg-surface-container-low p-space-md">
          {logLoading ? (
            <span className="font-small text-small text-secondary">جار التحميل…</span>
          ) : !log || log.length === 0 ? (
            <span className="font-small text-small text-secondary">لا تغييرات.</span>
          ) : (
            <ul className="flex flex-col gap-space-xs">
              {log.map((c) => (
                <li key={c.id} className="flex flex-wrap items-center justify-between gap-space-sm font-small text-small">
                  <span className="font-mono-body" dir="ltr">
                    {c.old_value ?? '—'} → {c.new_value}
                  </span>
                  <span className="font-mono-body text-outline" dir="ltr">{formatDateTime(c.changed_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </Card>
  )
}
