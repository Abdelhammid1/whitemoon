import { useEffect, useState } from 'react'
import { Wide } from '../layouts/AppShell'
import { Button, Card, EmptyState, InlineError, PageTitle, Pill, Spinner } from '../components/ui'
import { PageHelp } from '../components/PageHelp'
import { useToast } from '../components/Toast'
import { ApiError } from '../api/client'
import { formatDateTime } from '../lib/format'
import { answerGap, listGaps, type KnowledgeGap } from '../api/assistant'

const TABS: { code: string; label: string }[] = [
  { code: 'open', label: 'مفتوحة' },
  { code: 'answered', label: 'مُجابة' },
]

/** Why this gap was flagged. */
const SOURCE_AR: Record<string, string> = {
  retrieval: 'ضعف في المصادر',
  heuristic: 'المساعد اعتذر',
  judge: 'تقييم آلي للإجابة',
  user_feedback: 'بلاغ من المستخدم 👎',
}

export function KnowledgeGapsPage() {
  const toast = useToast()
  const [tab, setTab] = useState('open')
  const [rows, setRows] = useState<KnowledgeGap[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [drafts, setDrafts] = useState<Record<number, string>>({})
  const [busy, setBusy] = useState<number | null>(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      setRows((await listGaps(tab)).items)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'تعذّر التحميل')
    } finally {
      setLoading(false)
    }
  }
  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab])

  async function save(gap: KnowledgeGap) {
    const text = (drafts[gap.id] ?? '').trim()
    if (!text) return
    setBusy(gap.id)
    try {
      await answerGap(gap.id, text)
      toast.success('حُفظت الإجابة.')
      await load()
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : 'فشل الحفظ')
    } finally {
      setBusy(null)
    }
  }

  return (
    <Wide>
      <PageTitle title="فجوات المعرفة" subtitle="أسئلة لم يجد المساعد لها إجابة كافية — أضِف الإجابة لتتحسّن معرفته." />
      <PageHelp pageKey="assistant-gaps" />

      <div className="mt-space-lg flex items-center gap-space-xs">
        {TABS.map((t) => (
          <button
            key={t.code}
            type="button"
            onClick={() => setTab(t.code)}
            className={`rounded-full px-space-md py-space-xs font-small-medium text-small-medium transition-colors ${
              tab === t.code ? 'bg-primary text-on-primary' : 'bg-surface-variant text-on-surface-variant hover:text-primary'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      <div className="mt-space-lg">
        {loading ? (
          <Spinner />
        ) : error ? (
          <InlineError message={error} />
        ) : rows.length === 0 ? (
          <EmptyState title="لا توجد فجوات" description="كل الأسئلة في هذا التصنيف تمت تغطيتها." />
        ) : (
          <div className="flex flex-col gap-space-md">
            {rows.map((g) => (
              <Card key={g.id} className="flex flex-col gap-space-sm">
                <div className="flex flex-wrap items-center justify-between gap-space-sm">
                  <span className="font-body-medium text-body-medium text-on-surface">{g.question}</span>
                  <span className="inline-flex items-center gap-space-xs">
                    {g.source && <Pill tone="gold">{SOURCE_AR[g.source] ?? g.source}</Pill>}
                    <Pill tone={g.status === 'answered' ? 'signal' : 'warning'}>
                      {g.status === 'answered' ? 'مُجابة' : 'مفتوحة'}
                    </Pill>
                  </span>
                </div>
                <div className="flex flex-wrap gap-space-md font-small text-small text-secondary">
                  {g.route && <span>الصفحة: {g.route}</span>}
                  <span>{formatDateTime(g.created_at)}</span>
                </div>
                {g.detail && (
                  <p className="font-small text-small text-warning">سبب الرصد: {g.detail}</p>
                )}
                {g.assistant_answer && (
                  <details className="rounded-lg bg-surface-container-low px-space-md py-space-sm">
                    <summary className="cursor-pointer font-small-medium text-small-medium text-secondary">
                      رد المساعد وقتها
                    </summary>
                    <p className="mt-space-xs font-body text-body text-on-surface-variant whitespace-pre-wrap">
                      {g.assistant_answer}
                    </p>
                  </details>
                )}
                {g.status === 'answered' ? (
                  <p className="rounded-lg bg-surface-container-low p-space-md font-body text-body text-on-surface whitespace-pre-wrap">
                    {g.answer}
                  </p>
                ) : (
                  <div className="flex flex-col gap-space-sm">
                    <textarea
                      value={drafts[g.id] ?? ''}
                      onChange={(e) => setDrafts((d) => ({ ...d, [g.id]: e.target.value }))}
                      rows={3}
                      placeholder="اكتب الإجابة التي ستُضاف لمعرفة المساعد…"
                      className="w-full resize-none rounded-lg border border-surface-container-high bg-surface-container-lowest px-space-md py-space-sm font-body text-body text-on-surface focus:border-primary focus:outline-none"
                    />
                    <div className="flex justify-end">
                      <Button variant="primary" onClick={() => void save(g)} disabled={busy === g.id || !(drafts[g.id] ?? '').trim()}>
                        حفظ الإجابة
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </Wide>
  )
}
