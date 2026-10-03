/** Helpers for read endpoints that aren't built yet (frontend-only pass).
 *  A 404 means "endpoint pending" — we surface an empty state, never a crash. */

import { ApiError, api } from './client'

export class EndpointPending extends Error {}

export async function listOrPending<T>(path: string): Promise<T[]> {
  try {
    const resp = await api<{ items: T[] }>(path)
    return resp.items ?? []
  } catch (err) {
    if (err instanceof ApiError && (err.status === 404 || err.status === 405)) {
      throw new EndpointPending(path)
    }
    throw err
  }
}
