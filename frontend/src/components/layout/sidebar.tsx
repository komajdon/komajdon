import { NavLink } from 'react-router-dom'
import { cn } from '@/lib/utils'
import {
  Database, Plus, PieChart, Cpu,
  Table, Users, Key, Settings, ChevronLeft,
  Shield, FolderKanban, HardDrive, Gauge,
} from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'

interface NavItem {
  icon: React.ReactNode
  label: string
  to: string
}

const navSections: { title: string; items: NavItem[] }[] = [
  {
    title: 'Models',
    items: [
      { icon: <Database size={16} />, label: 'Collections', to: '/' },
      { icon: <Plus size={16} />, label: 'New Model', to: '/models/new' },
    ],
  },
  {
    title: 'APIs',
    items: [
      { icon: <PieChart size={16} />, label: 'Aggregations', to: '/aggregations' },
      { icon: <Cpu size={16} />, label: 'API Composer', to: '/composer' },
    ],
  },
  {
    title: 'Data',
    items: [
      { icon: <Table size={16} />, label: 'Data Explorer', to: '/data' },
      { icon: <HardDrive size={16} />, label: 'File Storage', to: '/storage' },
    ],
  },
  {
    title: 'Management',
    items: [
      { icon: <FolderKanban size={16} />, label: 'Projects', to: '/projects' },
      { icon: <Users size={16} />, label: 'Users', to: '/users' },
      { icon: <Shield size={16} />, label: 'Roles', to: '/roles' },
      { icon: <Key size={16} />, label: 'API Keys', to: '/keys' },
      { icon: <Gauge size={16} />, label: 'Rate Limits', to: '/rate-limits' },
    ],
  },
  {
    title: 'Settings',
    items: [
      { icon: <Settings size={16} />, label: 'Settings', to: '/settings' },
    ],
  },
]

export function Sidebar() {
  const open = useUIStore((s) => s.sidebarOpen)
  const toggle = useUIStore((s) => s.toggleSidebar)

  return (
    <aside className={cn(
      'fixed left-0 top-0 h-full bg-slate-900/80 backdrop-blur-xl border-r border-slate-800 z-40 transition-all duration-300 flex flex-col',
      open ? 'w-56' : 'w-16'
    )}>
      <div className={cn('flex items-center h-14 px-4 border-b border-slate-800', open ? 'justify-between' : 'justify-center')}>
        {open ? (
          <div className="flex items-center gap-2">
            <img src="/logo.png" alt="Komajdon" className="w-7 h-7 rounded-md" />
            <span className="font-semibold text-sm text-slate-100">Komajdon</span>
          </div>
        ) : (
          <img src="/logo.png" alt="Komajdon" className="w-7 h-7 rounded-md" />
        )}
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-2 space-y-6">
        {navSections.map((section) => (
          <div key={section.title}>
            {open && (
              <p className="px-3 text-[10px] font-semibold uppercase tracking-wider text-slate-500 mb-2">
                {section.title}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => cn(
                    'flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-all duration-200',
                    isActive
                      ? 'bg-mongodb-green/10 text-mongodb-green border border-mongodb-green/20'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/50',
                    !open && 'justify-center px-2'
                  )}
                  title={item.label}
                >
                  {item.icon}
                  {open && <span>{item.label}</span>}
                </NavLink>
              ))}
            </div>
          </div>
        ))}
      </nav>

      <div className="p-2 border-t border-slate-800">
        <button onClick={toggle} className="w-full flex items-center justify-center p-2 rounded-lg text-slate-500 hover:text-slate-300 hover:bg-slate-800/50 transition-all">
          <ChevronLeft size={16} className={cn('transition-transform', !open && 'rotate-180')} />
        </button>
      </div>
    </aside>
  )
}
