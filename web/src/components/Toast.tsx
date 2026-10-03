import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from 'react'

type ToastKind = 'info' | 'success' | 'error'
interface Toast { id: number; kind: ToastKind; message: string }
interface ToastApi { info: (m: string) => void; success: (m: string) => void; error: (m: string) => void }

const ToastContext = createContext<ToastApi | null>(null)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const nextId = useRef(1)

  const push = useCallback((kind: ToastKind, message: string) => {
    const id = nextId.current++
    setToasts((p) => [...p, { id, kind, message }])
    setTimeout(() => setToasts((p) => p.filter((t) => t.id !== id)), 4000)
  }, [])

  const api = useMemo<ToastApi>(
    () => ({ info: (m) => push('info', m), success: (m) => push('success', m), error: (m) => push('error', m) }),
    [push],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="pointer-events-none fixed inset-x-0 bottom-6 z-[60] flex flex-col items-center gap-space-sm px-space-lg">
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`pointer-events-auto overlay-shadow rounded-full bg-surface-container-lowest border px-space-md py-space-sm font-mono-body text-mono-body ${
              t.kind === 'error' ? 'border-[#B3261E]/40 text-[#B3261E]' : 'border-surface-container-high text-on-surface'
            }`}
          >
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastApi {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be inside <ToastProvider>')
  return ctx
}
