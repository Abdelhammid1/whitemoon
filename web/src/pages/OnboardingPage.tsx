import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Wide } from '../layouts/AppShell'
import { PageTitle, Button, Pill, Card, Spinner, InlineError } from '../components/ui'
import { Icon } from '../components/Icon'
import { PageHelp } from '../components/PageHelp'
import { useAuth } from '../auth/AuthContext'
import { getChecklist, type Onboarding, type OnboardingTask } from '../api/onboarding'
import { ApiError } from '../api/client'

function ackKey(userId: number, taskKey: string) {
  return `wm-onboarding-ack-${userId}-${taskKey}`
}

export function OnboardingPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [data, setData] = useState<Onboarding | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [acks, setAcks] = useState<Record<string, boolean>>({})

  const readAck = useCallback(
    (taskKey: string): boolean => {
      if (!user) return false
      try {
        return localStorage.getItem(ackKey(user.id, taskKey)) === '1'
      } catch {
        return false
      }
    },
    [user],
  )

  useEffect(() => {
    let alive = true
    setLoading(true)
    setError(null)
    getChecklist()
      .then((d) => {
        if (!alive) return
        setData(d)
        // Hydrate local acks for the 'ack' tasks this user already confirmed.
        const next: Record<string, boolean> = {}
        for (const t of d.tasks) {
          if (t.kind === 'ack') next[t.key] = readAck(t.key)
        }
        setAcks(next)
      })
      .catch((e) => {
        if (!alive) return
        setError(e instanceof ApiError ? e.message : 'تعذّر التحميل')
      })
      .finally(() => {
        if (alive) setLoading(false)
      })
    return () => {
      alive = false
    }
  }, [readAck])

  const isDone = useCallback(
    (t: OnboardingTask) => t.done || (t.kind === 'ack' && !!acks[t.key]),
    [acks],
  )

  const { completed, total, allDone } = useMemo(() => {
    if (!data) return { completed: 0, total: 0, allDone: false }
    const localAckDone = data.tasks.filter(
      (t) => t.kind === 'ack' && !t.done && acks[t.key],
    ).length
    const done = data.done_count + localAckDone
    return { completed: done, total: data.total, allDone: data.total > 0 && done >= data.total }
  }, [data, acks])

  function markAck(taskKey: string) {
    if (!user) return
    try {
      localStorage.setItem(ackKey(user.id, taskKey), '1')
    } catch {
      /* private mode / blocked storage — fine */
    }
    setAcks((prev) => ({ ...prev, [taskKey]: true }))
  }

  function hide() {
    if (user) {
      try {
        localStorage.setItem(`wm-onboarding-hidden-${user.id}`, '1')
      } catch {
        /* ignore */
      }
    }
    navigate('/home')
  }

  const pct = total > 0 ? Math.round((completed / total) * 100) : 0

  return (
    <Wide>
      <div className="flex items-start justify-between gap-space-md">
        <PageTitle
          title="كيف أبدأ؟"
          subtitle="خطوات إعداد حسابك — تُحدَّث تلقائيًا من بياناتك."
        />
        <Button onClick={hide} iconRight="visibility_off">
          إخفاء
        </Button>
      </div>

      <PageHelp pageKey="how-to-start" />

      {loading ? (
        <Spinner />
      ) : error || !data ? (
        <div className="mt-space-xl">
          <InlineError message={error ?? 'غير متاح'} />
        </div>
      ) : (
        <div className="mt-space-xl flex flex-col gap-space-md">
          {/* Progress */}
          <Card className="flex flex-col gap-space-md">
            <div className="flex items-center justify-between gap-space-md">
              <div className="flex flex-col">
                <span className="font-headline-2 text-headline-2 text-on-surface">تقدّم الإعداد</span>
                <span className="font-small text-small text-secondary mt-0.5">
                  <span className="font-mono-body" dir="ltr">
                    {completed}
                  </span>{' '}
                  من{' '}
                  <span className="font-mono-body" dir="ltr">
                    {total}
                  </span>
                </span>
              </div>
              {allDone && <Pill tone="signal">اكتمل الإعداد</Pill>}
            </div>
            <div className="h-2 rounded-full bg-surface-container overflow-hidden">
              <div
                className="h-full rounded-full bg-signal transition-all"
                style={{ width: `${pct}%` }}
              />
            </div>
          </Card>

          {/* Tasks */}
          <div className="flex flex-col gap-space-sm">
            {data.tasks.map((t) => {
              const done = isDone(t)
              return (
                <Card key={t.key} padded={false} className="px-space-lg py-space-md">
                  <div className="flex items-center gap-space-md">
                    <span
                      className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                        done ? 'bg-signal-weak text-signal' : 'border border-surface-container-high text-outline'
                      }`}
                    >
                      {done ? (
                        <Icon name="check" size={18} />
                      ) : (
                        <span className="w-2.5 h-2.5 rounded-full border border-outline" />
                      )}
                    </span>
                    <span className="flex-1 min-w-0 font-body-medium text-body-medium text-on-surface">
                      {t.label}
                    </span>
                    <div className="flex items-center gap-space-sm shrink-0">
                      {done ? (
                        <Pill tone="signal">تم</Pill>
                      ) : t.kind === 'ack' ? (
                        <>
                          <Button onClick={() => navigate(t.to)}>افتح</Button>
                          <Button variant="primary" onClick={() => markAck(t.key)}>
                            تم
                          </Button>
                        </>
                      ) : (
                        <Button variant="primary" onClick={() => navigate(t.to)}>
                          افتح
                        </Button>
                      )}
                    </div>
                  </div>
                </Card>
              )
            })}
          </div>
        </div>
      )}
    </Wide>
  )
}
