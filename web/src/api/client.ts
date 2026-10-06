/**
 * Fetch-based API client.
 *
 * Reads the access token from localStorage. On 401, tries exactly once
 * to refresh with the refresh token; on failure, clears auth and surfaces
 * the error so the UI can route to /login.
 */

export const API_BASE = '/api'

const ACCESS_KEY = 'wm.access'
const REFRESH_KEY = 'wm.refresh'

export const tokenStore = {
  getAccess(): string | null {
    try {
      return localStorage.getItem(ACCESS_KEY)
    } catch {
      return null
    }
  },
  getRefresh(): string | null {
    try {
      return localStorage.getItem(REFRESH_KEY)
    } catch {
      return null
    }
  },
  setPair(access: string, refresh: string | null): void {
    try {
      localStorage.setItem(ACCESS_KEY, access)
      if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    } catch {
      /* storage disabled; ignore */
    }
  },
  setAccess(access: string): void {
    try {
      localStorage.setItem(ACCESS_KEY, access)
    } catch {
      /* ignore */
    }
  },
  clear(): void {
    try {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
    } catch {
      /* ignore */
    }
  },
}

export class ApiError extends Error {
  readonly status: number
  readonly code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

async function parse(response: Response): Promise<unknown> {
  const text = await response.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

type Method = 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH'

interface RequestOpts {
  method?: Method
  body?: unknown
  // For token refresh — never retry the retry
  skipRefresh?: boolean
  // Omit the bearer header (used by /auth/login + /auth/register)
  anonymous?: boolean
  // Query string params
  query?: Record<string, string | number | undefined>
}

export async function api<T = unknown>(
  path: string,
  opts: RequestOpts = {},
): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Accept: 'application/json',
  }
  if (!opts.anonymous) {
    const token = tokenStore.getAccess()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  let url = `${API_BASE}${path}`
  if (opts.query) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(opts.query)) {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
    }
    const qs = params.toString()
    if (qs) url += (url.includes('?') ? '&' : '?') + qs
  }

  const resp = await fetch(url, {
    method: opts.method ?? 'GET',
    headers,
    body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
  })

  if (resp.ok) {
    return (await parse(resp)) as T
  }

  const payload = (await parse(resp)) as { error?: string; message?: string } | null

  if (resp.status === 401 && !opts.skipRefresh) {
    const refreshed = await tryRefresh()
    if (refreshed) {
      return api<T>(path, { ...opts, skipRefresh: true })
    }
  }

  const code = payload?.error ?? 'http_error'
  const message = payload?.message ?? `HTTP ${resp.status}`
  throw new ApiError(resp.status, code, message)
}

function buildUrl(path: string, query?: Record<string, string | number | undefined>): string {
  let url = `${API_BASE}${path}`
  if (query) {
    const params = new URLSearchParams()
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null && v !== '') params.set(k, String(v))
    }
    const qs = params.toString()
    if (qs) url += (url.includes('?') ? '&' : '?') + qs
  }
  return url
}

async function fetchBlob(path: string, query?: Record<string, string | number | undefined>): Promise<Blob> {
  const headers: Record<string, string> = {}
  const token = tokenStore.getAccess()
  if (token) headers.Authorization = `Bearer ${token}`
  const resp = await fetch(buildUrl(path, query), { headers })
  if (!resp.ok) {
    const payload = (await parse(resp)) as { error?: string; message?: string } | null
    throw new ApiError(resp.status, payload?.error ?? 'http_error', payload?.message ?? `HTTP ${resp.status}`)
  }
  return resp.blob()
}

/**
 * Open an authenticated document (PDF, or printable HTML on a dev box without
 * WeasyPrint) in a new tab. Fetches with the bearer token, then hands the
 * browser a blob URL so a plain link's missing Authorization header is a
 * non-issue. The blob URL is revoked after a minute to free memory.
 */
export async function openDocument(
  path: string,
  query?: Record<string, string | number | undefined>,
): Promise<void> {
  const blob = await fetchBlob(path, query)
  const url = URL.createObjectURL(blob)
  window.open(url, '_blank', 'noopener')
  setTimeout(() => URL.revokeObjectURL(url), 60_000)
}

/** Download an authenticated file (e.g. an .xlsx export) to disk. */
export async function downloadFile(
  path: string,
  filename: string,
  query?: Record<string, string | number | undefined>,
): Promise<void> {
  const blob = await fetchBlob(path, query)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

/** POST multipart form-data with the bearer token (for file uploads). */
export async function postForm<T = unknown>(path: string, form: FormData): Promise<T> {
  const headers: Record<string, string> = {}
  const token = tokenStore.getAccess()
  if (token) headers.Authorization = `Bearer ${token}`
  const resp = await fetch(buildUrl(path), { method: 'POST', headers, body: form })
  if (resp.ok) return (await parse(resp)) as T
  const payload = (await parse(resp)) as { error?: string; message?: string } | null
  throw new ApiError(resp.status, payload?.error ?? 'http_error', payload?.message ?? `HTTP ${resp.status}`)
}

async function tryRefresh(): Promise<boolean> {
  const refresh = tokenStore.getRefresh()
  if (!refresh) {
    tokenStore.clear()
    return false
  }
  try {
    const resp = await fetch(`${API_BASE}/auth/refresh`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${refresh}` },
    })
    if (!resp.ok) {
      tokenStore.clear()
      return false
    }
    const body = (await resp.json()) as { access_token?: string }
    if (!body.access_token) {
      tokenStore.clear()
      return false
    }
    tokenStore.setAccess(body.access_token)
    return true
  } catch {
    tokenStore.clear()
    return false
  }
}
