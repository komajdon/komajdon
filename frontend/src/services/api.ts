import type { TokenResponse } from '@/types'

const BASE = ''

class ApiService {
  private token: string | null = null
  private refreshToken: string | null = null
  private projectId: string | null = null

  constructor() {
    this.token = localStorage.getItem('komajdon_token')
    this.refreshToken = localStorage.getItem('komajdon_refresh')
    this.projectId = localStorage.getItem('komajdon_project')
  }

  setToken(token: string | null) {
    this.token = token
    if (token) localStorage.setItem('komajdon_token', token)
    else localStorage.removeItem('komajdon_token')
  }

  getToken() {
    return this.token
  }

  setRefreshToken(token: string | null) {
    this.refreshToken = token
    if (token) localStorage.setItem('komajdon_refresh', token)
    else localStorage.removeItem('komajdon_refresh')
  }

  setProjectId(id: string | null) {
    this.projectId = id
    if (id) localStorage.setItem('komajdon_project', id)
    else localStorage.removeItem('komajdon_project')
  }

  async refreshAuth(): Promise<boolean> {
    if (!this.refreshToken) return false
    try {
      const r = await fetch(`${BASE}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: this.refreshToken }),
      })
      if (!r.ok) return false
      const data: TokenResponse = await r.json()
      this.setToken(data.access_token)
      this.setRefreshToken(data.refresh_token)
      return true
    } catch {
      return false
    }
  }

  async request<T>(
    method: string,
    path: string,
    body?: unknown,
    attempt = 1
  ): Promise<T> {
    const headers: Record<string, string> = {}
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`
    if (this.projectId) headers['X-Project-Id'] = this.projectId

    const opts: RequestInit = { method, headers }

    if (body && !(body instanceof FormData)) {
      headers['Content-Type'] = 'application/json'
      opts.body = JSON.stringify(body)
    } else if (body instanceof FormData) {
      opts.body = body
    }

    const res = await fetch(`${BASE}${path}`, opts)

    if (res.status === 401 && attempt === 1 && await this.refreshAuth()) {
      return this.request<T>(method, path, body, 2)
    }

    if (method === 'DELETE' && res.status === 204) return null as T

    const contentType = res.headers.get('content-type') || ''
    const data = contentType.includes('application/json')
      ? await res.json()
      : await res.text()

    if (!res.ok) {
      const msg = typeof data === 'string' ? data : data?.detail || JSON.stringify(data)
      throw new Error(msg)
    }

    return data as T
  }

  get<T>(path: string) { return this.request<T>('GET', path) }
  post<T>(path: string, body?: unknown) { return this.request<T>('POST', path, body) }
  patch<T>(path: string, body?: unknown) { return this.request<T>('PATCH', path, body) }
  put<T>(path: string, body?: unknown) { return this.request<T>('PUT', path, body) }
  delete<T>(path: string) { return this.request<T>('DELETE', path) }

  upload<T>(path: string, formData: FormData) {
    const headers: Record<string, string> = {}
    if (this.token) headers['Authorization'] = `Bearer ${this.token}`
    if (this.projectId) headers['X-Project-Id'] = this.projectId
    return fetch(`${BASE}${path}`, { method: 'POST', headers, body: formData }).then(
      async (res) => {
        const data = await res.json()
        if (!res.ok) throw new Error(data.detail || 'Upload failed')
        return data as T
      }
    )
  }
}

export const api = new ApiService()
