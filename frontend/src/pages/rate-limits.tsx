import { useEffect, useState } from 'react'
import { Gauge, Plus, Trash2, Edit3, ToggleLeft, ToggleRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { api } from '@/services/api'
import { useUIStore } from '@/stores/uiStore'
import { getMethodBadgeClass } from '@/lib/utils'
import type { RateLimitRule } from '@/types'

const METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', '*']

export function RateLimitsPage() {
  const [rules, setRules] = useState<RateLimitRule[]>([])
  const toast = useUIStore((s) => s.toast)

  const [showCreate, setShowCreate] = useState(false)
  const [endpoint, setEndpoint] = useState('')
  const [method, setMethod] = useState('*')
  const [maxReq, setMaxReq] = useState(60)
  const [windowSec, setWindowSec] = useState(60)
  const [description, setDescription] = useState('')

  const [showEdit, setShowEdit] = useState(false)
  const [editId, setEditId] = useState('')
  const [editEndpoint, setEditEndpoint] = useState('')
  const [editMethod, setEditMethod] = useState('*')
  const [editMaxReq, setEditMaxReq] = useState(60)
  const [editWindowSec, setEditWindowSec] = useState(60)
  const [editDescription, setEditDescription] = useState('')

  useEffect(() => { loadData() }, [])

  const loadData = async () => {
    try {
      const data = await api.get<RateLimitRule[]>('/api/rate-limits/')
      setRules(data)
    } catch { /* ignore */ }
  }

  const handleCreate = async () => {
    try {
      await api.post('/api/rate-limits/', {
        endpoint, method, max_requests: maxReq,
        window_seconds: windowSec, description,
      })
      toast('Rate limit rule created', 'success')
      setShowCreate(false)
      setEndpoint(''); setMethod('*'); setMaxReq(60); setWindowSec(60); setDescription('')
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleEdit = async () => {
    try {
      await api.put(`/api/rate-limits/${editId}`, {
        endpoint: editEndpoint, method: editMethod,
        max_requests: editMaxReq, window_seconds: editWindowSec,
        description: editDescription,
      })
      toast('Rate limit rule updated', 'success')
      setShowEdit(false)
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleDelete = async (ruleId: string) => {
    try {
      await api.delete(`/api/rate-limits/${ruleId}`)
      toast('Rule deleted', 'success')
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleToggle = async (rule: RateLimitRule) => {
    try {
      await api.put(`/api/rate-limits/${rule.id}`, { enabled: !rule.enabled })
      toast(rule.enabled ? 'Rule disabled' : 'Rule enabled', 'success')
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-slate-100">Rate Limits</h1>
          <p className="text-xs text-slate-500 mt-1">
            Configure per-endpoint rate limiting rules. Rules override the global defaults.
          </p>
        </div>
        <Button size="sm" onClick={() => setShowCreate(true)}>
          <Plus size={14} className="mr-1" /> New Rule
        </Button>
      </div>

      <div className="bg-slate-800/20 border border-slate-700/30 rounded-xl p-4 mb-6">
        <h3 className="text-sm font-medium text-slate-400 mb-2">Global Defaults</h3>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 text-xs">
          <div className="bg-slate-800/30 rounded-lg p-3">
            <span className="text-slate-500">General API</span>
            <p className="text-lg font-semibold text-slate-200 mt-1">60 req/min</p>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3">
            <span className="text-slate-500">Auth endpoints</span>
            <p className="text-lg font-semibold text-slate-200 mt-1">10 req/min</p>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3">
            <span className="text-slate-500">Custom rules</span>
            <p className="text-lg font-semibold text-slate-200 mt-1">{rules.length}</p>
          </div>
          <div className="bg-slate-800/30 rounded-lg p-3">
            <span className="text-slate-500">Window</span>
            <p className="text-lg font-semibold text-slate-200 mt-1">60s</p>
          </div>
        </div>
      </div>

      {rules.length === 0 ? (
        <div className="text-center py-16 text-slate-500">
          <Gauge size={40} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No custom rate limit rules yet.</p>
          <p className="text-xs mt-1">Create a rule to override rate limits for specific endpoints.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {rules.map((rule) => (
            <div key={rule.id} className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 flex items-center justify-between">
              <div className="flex items-center gap-4 flex-1 min-w-0">
                <button onClick={() => handleToggle(rule)} className="shrink-0 text-slate-500 hover:text-slate-300 transition-colors">
                  {rule.enabled ? <ToggleRight size={22} className="text-emerald-400" /> : <ToggleLeft size={22} />}
                </button>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className={`text-[10px] font-mono font-bold px-1.5 py-0.5 rounded ${getMethodBadgeClass(rule.method)}`}>{rule.method}</span>
                    <code className="text-sm font-mono text-slate-200 truncate">{rule.endpoint}</code>
                  </div>
                  {rule.description && (
                    <p className="text-[11px] text-slate-500 mt-1 ml-12 truncate">{rule.description}</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-6 shrink-0 ml-4">
                <div className="text-right">
                  <p className="text-sm font-semibold text-slate-200">{rule.max_requests}</p>
                  <p className="text-[10px] text-slate-500">req/{rule.window_seconds}s</p>
                </div>
                <div className="flex gap-1">
                  <button
                    onClick={() => {
                      setEditId(rule.id); setEditEndpoint(rule.endpoint); setEditMethod(rule.method)
                      setEditMaxReq(rule.max_requests); setEditWindowSec(rule.window_seconds)
                      setEditDescription(rule.description); setShowEdit(true)
                    }}
                    className="text-slate-500 hover:text-slate-300 p-1"
                  >
                    <Edit3 size={14} />
                  </button>
                  <button onClick={() => handleDelete(rule.id)} className="text-slate-500 hover:text-red-400 p-1">
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="New Rate Limit Rule">
        <div className="space-y-4">
          <div>
            <p className="text-xs text-slate-500 mb-3">
              Set custom rate limits for a specific API endpoint. Use <code className="text-emerald-400">*</code> method to match all HTTP methods.
            </p>
          </div>
          <Input label="Endpoint" value={endpoint} onChange={(e) => setEndpoint(e.target.value)} placeholder="/api/auth/signin" />
          <div>
            <p className="text-sm font-medium text-slate-400 mb-2">HTTP Method</p>
            <div className="flex gap-2">
              {METHODS.map((m) => (
                <button
                  key={m}
                  onClick={() => setMethod(m)}
                  className={`text-[11px] font-mono px-3 py-1.5 rounded-lg border transition-all ${
                    method === m
                      ? 'bg-emerald-900/30 border-emerald-500/50 text-emerald-400'
                      : 'bg-slate-800/50 border-slate-700/50 text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {m === '*' ? 'ALL' : m}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Max Requests" type="number" value={String(maxReq)} onChange={(e) => setMaxReq(Number(e.target.value))} min={1} max={10000} />
            <Input label="Window (seconds)" type="number" value={String(windowSec)} onChange={(e) => setWindowSec(Number(e.target.value))} min={1} max={86400} />
          </div>
          <Input label="Description (optional)" value={description} onChange={(e) => setDescription(e.target.value)} placeholder="e.g. Strict rate limit for signin" />
          <Button className="w-full" onClick={handleCreate}>Create Rule</Button>
        </div>
      </Modal>

      <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Rate Limit Rule">
        <div className="space-y-4">
          <Input label="Endpoint" value={editEndpoint} onChange={(e) => setEditEndpoint(e.target.value)} />
          <div>
            <p className="text-sm font-medium text-slate-400 mb-2">HTTP Method</p>
            <div className="flex gap-2">
              {METHODS.map((m) => (
                <button
                  key={m}
                  onClick={() => setEditMethod(m)}
                  className={`text-[11px] font-mono px-3 py-1.5 rounded-lg border transition-all ${
                    editMethod === m
                      ? 'bg-emerald-900/30 border-emerald-500/50 text-emerald-400'
                      : 'bg-slate-800/50 border-slate-700/50 text-slate-500 hover:text-slate-300'
                  }`}
                >
                  {m === '*' ? 'ALL' : m}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Max Requests" type="number" value={String(editMaxReq)} onChange={(e) => setEditMaxReq(Number(e.target.value))} min={1} max={10000} />
            <Input label="Window (seconds)" type="number" value={String(editWindowSec)} onChange={(e) => setEditWindowSec(Number(e.target.value))} min={1} max={86400} />
          </div>
          <Input label="Description (optional)" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
          <Button className="w-full" onClick={handleEdit}>Save Changes</Button>
        </div>
      </Modal>
    </div>
  )
}