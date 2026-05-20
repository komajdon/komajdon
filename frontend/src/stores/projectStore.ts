import { create } from 'zustand'
import { api } from '@/services/api'
import { useModelStore } from '@/stores/modelStore'
import type { Project } from '@/types'

interface ProjectState {
  projects: Project[]
  activeProject: Project | null
  loading: boolean
  loadProjects: () => Promise<void>
  createProject: (name: string, slug: string, description?: string) => Promise<void>
  selectProject: (project: Project | null) => void
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  activeProject: null,
  loading: false,

  loadProjects: async () => {
    try {
      const projects = await api.get<Project[]>('/api/projects/')
      set({ projects })
    } catch { /* ignore */ }
  },

  createProject: async (name, slug, description = '') => {
    await api.post('/api/projects/', { name, slug, description })
    const projects = await api.get<Project[]>('/api/projects/')
    set({ projects })
  },

  selectProject: (project) => {
    api.setProjectId(project?.id || null)
    set({ activeProject: project })
    const ms = useModelStore.getState()
    ms.loadModels()
    ms.loadPipelines()
  },
}))
