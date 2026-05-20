import { useRef, useEffect, useState, useCallback } from 'react'
import { cn } from '@/lib/utils'

interface JSONEditorProps {
  value: string
  onChange?: (value: string) => void
  height?: string
  readOnly?: boolean
  className?: string
}

export function JSONEditor({ value, onChange, height = '200px', readOnly, className }: JSONEditorProps) {
  const [local, setLocal] = useState(value)
  const [error, setError] = useState<string | null>(null)
  const isSync = useRef(true)

  useEffect(() => {
    if (isSync.current) {
      setLocal(value)
      setError(null)
    }
  }, [value])

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const v = e.target.value
      setLocal(v)
      isSync.current = false
      try {
        JSON.parse(v)
        setError(null)
        onChange?.(v)
      } catch {
        setError('Invalid JSON')
      }
    },
    [onChange]
  )

  const formatJson = useCallback(() => {
    try {
      const formatted = JSON.stringify(JSON.parse(local), null, 2)
      setLocal(formatted)
      setError(null)
      onChange?.(formatted)
    } catch {
      // ignore
    }
  }, [local, onChange])

  return (
    <div className={cn('relative rounded-lg border border-slate-700 overflow-hidden', className)}>
      <div className="flex items-center justify-between px-3 py-1.5 bg-slate-800/50 border-b border-slate-700">
        <span className="text-xs text-slate-500">
          {error ? (
            <span className="text-red-400">{error}</span>
          ) : (
            'JSON'
          )}
        </span>
        {!readOnly && (
          <button
            onClick={formatJson}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors"
          >
            Format
          </button>
        )}
      </div>
      <textarea
        value={local}
        onChange={handleChange}
        readOnly={readOnly}
        spellCheck={false}
        className={cn(
          'w-full bg-slate-900 p-3 font-mono text-xs leading-relaxed text-slate-200 resize-none focus:outline-none',
          error && 'text-red-300'
        )}
        style={{ height }}
      />
    </div>
  )
}
