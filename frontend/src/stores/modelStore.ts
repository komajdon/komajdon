import { create } from 'zustand'
import { api } from '@/services/api'
import type { ModelSchema, GenerateRequest, AggregationPipeline } from '@/types'

interface ModelState {
  models: ModelSchema[]
  pipelines: AggregationPipeline[]
  loading: boolean
  loadModels: () => Promise<void>
  loadPipelines: () => Promise<void>
  createModel: (req: GenerateRequest) => Promise<ModelSchema>
  deleteModel: (name: string) => Promise<void>
}

export const useModelStore = create<ModelState>((set) => ({
  models: [],
  pipelines: [],
  loading: false,

  loadModels: async () => {
    set({ loading: true })
    try {
      const models = await api.get<ModelSchema[]>('/api/models/')
      set({ models, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  loadPipelines: async () => {
    try {
      const pipelines = await api.get<AggregationPipeline[]>('/api/pipelines/')
      set({ pipelines })
    } catch { /* ignore */ }
  },

  createModel: async (req) => {
    const result = await api.post<{ message: string; id: string }>('/api/models/', req)
    const models = await api.get<ModelSchema[]>('/api/models/')
    set({ models })
    return {
      _id: result.id, name: req.name, fields: req.fields,
      indexes: req.indexes || [],
      auth_protected: req.auth_protected || false,
      realtime_enabled: req.realtime_enabled || false,
      created_at: '',
    }
  },

  deleteModel: async (name) => {
    await api.delete(`/api/models/${name}`)
    set((s) => ({ models: s.models.filter((m) => m.name !== name) }))
  },
}))
