export class TransportError extends Error {
  status: number

  constructor(status: number) {
    super(`transport:${status}`)
    this.status = status
  }
}

export async function fetchJson(path: string, options: RequestInit = {}) {
  const response = await fetch(path, { cache: "no-store", ...options })
  if (!response.ok) throw new TransportError(response.status)
  return response.json() as Promise<unknown>
}
