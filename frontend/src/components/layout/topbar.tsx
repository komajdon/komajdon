import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, User, FolderKanban, Check, ChevronDown } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useProjectStore } from '@/stores/projectStore'
import { useUIStore } from '@/stores/uiStore'

export function Topbar() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const toast = useUIStore((s) => s.toast)
  const navigate = useNavigate()
  const projects = useProjectStore((s) => s.projects)
  const activeProject = useProjectStore((s) => s.activeProject)
  const loadProjects = useProjectStore((s) => s.loadProjects)
  const selectProject = useProjectStore((s) => s.selectProject)
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (user) loadProjects()
  }, [user, loadProjects])

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleLogout = async () => {
    await logout()
    toast('Logged out', 'info')
    navigate('/login')
  }

  return (
    <header className="h-14 border-b border-slate-800 bg-slate-900/50 backdrop-blur-xl flex items-center justify-between px-6">
      <div className="flex items-center gap-3">
        <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
        <span className="text-xs text-emerald-400 font-medium">Connected</span>

        {/* Project selector */}
        <div className="relative ml-4" ref={ref}>
          <button
            onClick={() => setOpen(!open)}
            className="flex items-center gap-2 text-xs text-slate-400 hover:text-slate-200 bg-slate-800/50 px-3 py-1.5 rounded-lg border border-slate-700/50"
          >
            <FolderKanban size={12} />
            <span>{activeProject ? activeProject.name : 'Global'}</span>
            <ChevronDown size={12} className={open ? 'rotate-180' : ''} />
          </button>
          {open && (
            <div className="absolute top-full mt-1 left-0 w-48 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-50 py-1">
              <button
                onClick={() => { selectProject(null); setOpen(false) }}
                className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-700/50 flex items-center gap-2 ${!activeProject ? 'text-mongodb-green' : 'text-slate-400'}`}
              >
                <FolderKanban size={12} />
                Global (no project)
                {!activeProject && <Check size={12} className="ml-auto" />}
              </button>
              {projects.map((p) => (
                <button
                  key={p.id}
                  onClick={() => { selectProject(p); setOpen(false) }}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-700/50 flex items-center gap-2 ${activeProject?.id === p.id ? 'text-mongodb-green' : 'text-slate-400'}`}
                >
                  <FolderKanban size={12} />
                  {p.name}
                  {activeProject?.id === p.id && <Check size={12} className="ml-auto" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2">
            <span className={`text-[10px] font-medium px-2 py-0.5 rounded-full ${user.role === 'admin' ? 'bg-amber-500/20 text-amber-400' : 'bg-blue-500/20 text-blue-400'}`}>
              {user.role}
            </span>
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <User size={14} />
              {user.email}
            </div>
          </div>
        )}
        <button onClick={handleLogout} className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-300 transition-colors">
          <LogOut size={14} />
          Logout
        </button>
      </div>
    </header>
  )
}
