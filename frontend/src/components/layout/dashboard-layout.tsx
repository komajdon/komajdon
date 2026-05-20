import { Outlet } from 'react-router-dom'
import { Sidebar } from './sidebar'
import { Topbar } from './topbar'
import { ToastContainer } from '@/components/ui/toast'
import { useUIStore } from '@/stores/uiStore'
import { cn } from '@/lib/utils'

export function DashboardLayout() {
  const sidebarOpen = useUIStore((s) => s.sidebarOpen)

  return (
    <div className="min-h-screen bg-slate-950">
      <Sidebar />
      <div
        className={cn(
          'transition-all duration-300',
          sidebarOpen ? 'ml-56' : 'ml-16'
        )}
      >
        <Topbar />
        <main>
          <Outlet />
        </main>
      </div>
      <ToastContainer />
    </div>
  )
}
