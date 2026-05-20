import { create } from 'zustand'
import { api } from '@/services/api'
import type { User, TokenResponse } from '@/types'

interface AuthState {
  user: User | null
  loading: boolean
  signin: (email: string, password: string) => Promise<void>
  signup: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  checkAuth: () => Promise<boolean>
  forgotPassword: (email: string) => Promise<string>
  resetPassword: (token: string, password: string) => Promise<string>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,

  signin: async (email, password) => {
    const data = await api.post<TokenResponse>('/api/auth/signin', { email, password })
    api.setToken(data.access_token)
    api.setRefreshToken(data.refresh_token)
    set({ user: data.user })
  },

  signup: async (email, password) => {
    const data = await api.post<TokenResponse>('/api/auth/signup', { email, password })
    api.setToken(data.access_token)
    api.setRefreshToken(data.refresh_token)
    set({ user: data.user })
  },

  logout: async () => {
    const refresh = localStorage.getItem('komajdon_refresh')
    try {
      if (refresh) {
        await api.post('/api/auth/logout', { refresh_token: refresh })
      }
    } catch (e) {
      console.warn('[komajdon] Logout server invalidation failed:', e)
    }
    api.setToken(null)
    api.setRefreshToken(null)
    set({ user: null })
  },

  checkAuth: async () => {
    if (!api.getToken()) return false
    set({ loading: true })
    try {
      const user = await api.get<User>('/api/auth/me')
      set({ user, loading: false })
      return true
    } catch {
      if (await api.refreshAuth()) {
        try {
          const user = await api.get<User>('/api/auth/me')
          set({ user, loading: false })
          return true
        } catch { /* fall through */ }
      }
      api.setToken(null)
      api.setRefreshToken(null)
      set({ user: null, loading: false })
      return false
    }
  },

  forgotPassword: async (email) => {
    const r = await api.post<{ message: string }>('/api/auth/forgot-password', { email })
    return r.message
  },

  resetPassword: async (token, new_password) => {
    const r = await api.post<{ message: string }>('/api/auth/reset-password', { token, new_password })
    return r.message
  },
}))
