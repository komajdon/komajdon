import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function truncateId(id: string, len = 8): string {
  return id.length > len ? id.slice(0, len) + '...' : id
}

export function getErrorMessage(e: unknown, fallback = 'Failed'): string {
  return e instanceof Error ? e.message : fallback
}

export function getMethodBadgeClass(method: string): string {
  switch (method) {
    case 'GET':
      return 'bg-emerald-500/20 text-emerald-400'
    case 'POST':
      return 'bg-blue-500/20 text-blue-400'
    case 'PATCH':
      return 'bg-yellow-500/20 text-yellow-400'
    case 'PUT':
      return 'bg-orange-500/20 text-orange-400'
    case 'DELETE':
      return 'bg-red-500/20 text-red-400'
    default:
      return 'bg-slate-600 text-slate-300'
  }
}


