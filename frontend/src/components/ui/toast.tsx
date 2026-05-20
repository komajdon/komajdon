import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'
import { useUIStore } from '@/stores/uiStore'
import { cn } from '@/lib/utils'

const icons = {
  success: CheckCircle,
  error: XCircle,
  info: Info,
}

const colors = {
  success: 'border-l-emerald-500 bg-emerald-500/10',
  error: 'border-l-red-500 bg-red-500/10',
  info: 'border-l-blue-500 bg-blue-500/10',
}

export function ToastContainer() {
  const toasts = useUIStore((s) => s.toasts)
  const dismissToast = useUIStore((s) => s.dismissToast)

  if (!toasts.length) return null

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 max-w-sm">
      <AnimatePresence>
        {toasts.map((t) => {
          const Icon = icons[t.type]
          return (
            <motion.div
              key={t.id}
              initial={{ opacity: 0, x: 100, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 100, scale: 0.95 }}
              className={cn(
                'flex items-start gap-3 px-4 py-3 rounded-lg border border-slate-700 shadow-xl backdrop-blur-sm',
                colors[t.type]
              )}
            >
              <Icon size={18} className="shrink-0 mt-0.5 text-slate-300" />
              <p className="text-sm text-slate-200 flex-1">{t.message}</p>
              <button onClick={() => dismissToast(t.id)} className="text-slate-500 hover:text-slate-300">
                <X size={14} />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
