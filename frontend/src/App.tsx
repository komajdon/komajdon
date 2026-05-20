import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import { useModelStore } from '@/stores/modelStore'
import { DashboardLayout } from '@/components/layout/dashboard-layout'
import { LoginPage } from '@/pages/login'
import { DashboardPage } from '@/pages/dashboard'
import { ModelBuilderPage } from '@/pages/model-builder'
import { ModelDetailPage } from '@/pages/model-detail'
import { DataExplorerPage } from '@/pages/data-explorer'
import { AggregationsPage } from '@/pages/aggregations'
import { ApiComposerPage } from '@/pages/api-composer'
import { ProjectsPage } from '@/pages/projects'
import { UsersPage } from '@/pages/users'
import { RolesPage } from '@/pages/roles'
import { ApiKeysPage } from '@/pages/api-keys'
import { SettingsPage } from '@/pages/settings'
import { StoragePage } from '@/pages/storage'
import { RateLimitsPage } from '@/pages/rate-limits'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const user = useAuthStore((s) => s.user)
  if (!user) return <Navigate to="/login" replace />
  return <>{children}</>
}

function AuthGuard() {
  const user = useAuthStore((s) => s.user)
  const loading = useAuthStore((s) => s.loading)
  if (loading) return null
  if (user) return <Navigate to="/" replace />
  return <LoginPage />
}

export default function App() {
  const user = useAuthStore((s) => s.user)
  const checkAuth = useAuthStore((s) => s.checkAuth)
  const loadModels = useModelStore((s) => s.loadModels)
  const loadPipelines = useModelStore((s) => s.loadPipelines)

  useEffect(() => { checkAuth() }, [checkAuth])

  useEffect(() => {
    if (user) {
      loadModels()
      loadPipelines()
    }
  }, [user, loadModels, loadPipelines])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<AuthGuard />} />
        <Route element={<ProtectedRoute><DashboardLayout /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="models/new" element={<ModelBuilderPage />} />
          <Route path="models/:name/edit" element={<ModelBuilderPage />} />
          <Route path="models/:name" element={<ModelDetailPage />} />
          <Route path="data" element={<DataExplorerPage />} />
          <Route path="aggregations" element={<AggregationsPage />} />
          <Route path="composer" element={<ApiComposerPage />} />
          <Route path="projects" element={<ProjectsPage />} />
          <Route path="users" element={<UsersPage />} />
          <Route path="roles" element={<RolesPage />} />
          <Route path="keys" element={<ApiKeysPage />} />
          <Route path="rate-limits" element={<RateLimitsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="storage" element={<StoragePage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
