import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Plus, Trash2, Play, Globe, Edit3,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { JSONEditor } from '@/components/ui/json-editor'
import { useModelStore } from '@/stores/modelStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'
import type { AggregationStage } from '@/types'

const STAGE_TYPES = [
  'match', 'group', 'sort', 'project', 'limit',
  'skip', 'lookup', 'unwind', 'count', 'add_fields',
]

export function AggregationsPage() {
  const pipelines = useModelStore((s) => s.pipelines)
  const loadPipelines = useModelStore((s) => s.loadPipelines)
  const models = useModelStore((s) => s.models)
  const navigate = useNavigate()
  const toast = useUIStore((s) => s.toast)

  const [showBuilder, setShowBuilder] = useState(false)
  const [pipeName, setPipeName] = useState('')
  const [pipeCollection, setPipeCollection] = useState(models[0]?.name || '')
  const [stages, setStages] = useState<{ type: string; params: string }[]>([])
  const [runningId, setRunningId] = useState<string | null>(null)
  const [runResult, setRunResult] = useState<string | null>(null)
  const [exposingId, setExposingId] = useState<string | null>(null)
  const [editingPipeline, setEditingPipeline] = useState<{ id: string; name: string; collection: string; stages: { type: string; params: string }[] } | null>(null)
  const [showEdit, setShowEdit] = useState(false)
  const [editName, setEditName] = useState('')
  const [editCollection, setEditCollection] = useState(models[0]?.name || '')
  const [editStages, setEditStages] = useState<{ type: string; params: string }[]>([])

  useEffect(() => {
    loadPipelines()
  }, [loadPipelines])

  const startEdit = (p: typeof pipelines[0]) => {
    setEditName(p.name)
    setEditCollection(p.collection)
    setEditStages(p.stages.map(s => ({ type: s.type, params: JSON.stringify(s.params) })))
    setEditingPipeline({ id: p._id, name: p.name, collection: p.collection, stages: [] })
    setShowEdit(true)
  }

  const saveEdit = async () => {
    if (!editingPipeline) return
    if (!editName || !editCollection) { toast('Name and collection required', 'error'); return }
    try {
      const parsedStages: AggregationStage[] = editStages.map((s) => ({
        type: s.type,
        params: JSON.parse(s.params || '{}'),
      }))
      await api.put(`/api/pipelines/${editingPipeline.id}`, { name: editName, collection: editCollection, stages: parsedStages })
      toast('Pipeline updated', 'success')
      setShowEdit(false)
      setEditingPipeline(null)
      loadPipelines()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Update failed', 'error')
    }
  }

  const addStage = () => setStages((prev) => [...prev, { type: 'match', params: '{}' }])

  const updateStage = (idx: number, updates: Partial<{ type: string; params: string }>) => {
    setStages((prev) => prev.map((s, i) => (i === idx ? { ...s, ...updates } : s)))
  }

  const removeStage = (idx: number) => setStages((prev) => prev.filter((_, i) => i !== idx))

  const savePipeline = async () => {
    if (!pipeName || !pipeCollection) {
      toast('Name and collection required', 'error')
      return
    }
    try {
      const parsedStages: AggregationStage[] = stages.map((s) => ({
        type: s.type,
        params: JSON.parse(s.params || '{}'),
      }))
      await api.post('/api/pipelines/', { name: pipeName, collection: pipeCollection, stages: parsedStages })
      toast('Pipeline created', 'success')
      setShowBuilder(false)
      loadPipelines()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Save failed', 'error')
    }
  }

  const runPipeline = async (id: string) => {
    setRunningId(id)
    setRunResult(null)
    try {
      const data = await api.post(`/api/pipelines/run/${id}`, {})
      setRunResult(JSON.stringify(data, null, 2))
    } catch (e: unknown) {
      setRunResult(`Error: ${e instanceof Error ? e.message : 'Run failed'}`)
    } finally {
      setRunningId(null)
    }
  }

  const deletePipeline = async (id: string) => {
    if (!confirm('Delete this pipeline?')) return
    try {
      await api.delete(`/api/pipelines/${id}`)
      toast('Deleted', 'info')
      loadPipelines()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft size={16} />
          </Button>
          <h1 className="text-2xl font-bold text-slate-100">Aggregation Pipelines</h1>
        </div>
        <Button onClick={() => { setPipeName(''); setStages([]); setShowBuilder(true) }}>
          <Plus size={16} /> New Pipeline
        </Button>
      </div>

      {pipelines.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-slate-500 mb-4">No pipelines yet. Create your first aggregation pipeline.</p>
          <Button onClick={() => { setPipeName(''); setStages([]); setShowBuilder(true) }}>
            Create Pipeline
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {pipelines.map((p) => (
            <motion.div
              key={p._id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5"
            >
              <div className="flex items-center justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-200">{p.name}</h3>
                  <p className="text-sm text-slate-500">
                    Collection: {p.collection} · {p.stages.length} stages
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => startEdit(p)}>
                    <Edit3 size={12} /> Edit
                  </Button>
                  <Button size="sm" loading={exposingId === p._id} onClick={async () => {
                    setExposingId(p._id)
                    try {
                      await api.post(`/api/pipelines/${p._id}/expose`, { expose_as_api: true, api_method: 'GET' })
                      toast(`Exposed at /api/aggregated/${p.name}`, 'success')
                      loadPipelines()
                    } catch (e: any) { toast(e.message, 'error') }
                    finally { setExposingId(null) }
                  }}>
                    <Globe size={12} /> Expose
                  </Button>
                  <Button size="sm" loading={runningId === p._id} onClick={() => runPipeline(p._id)}>
                    <Play size={12} /> Run
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => deletePipeline(p._id)}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              </div>
              {p.stages.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {p.stages.map((s, i) => (
                    <span key={i} className="px-2 py-1 bg-slate-800 rounded text-xs text-slate-400 font-mono border border-slate-700">
                      ${s.type}
                    </span>
                  ))}
                </div>
              )}
              {runResult && runningId !== p._id && (
                <pre className="mt-3 text-xs text-slate-400 font-mono max-h-32 overflow-y-auto">
                  {runResult}
                </pre>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* Builder Modal */}
      <Modal open={showBuilder} onClose={() => setShowBuilder(false)} title="New Pipeline" size="lg">
        <div className="space-y-4">
          <Input label="Pipeline Name" value={pipeName} onChange={(e) => setPipeName(e.target.value)} />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-400">Collection</label>
            <select
              value={pipeCollection}
              onChange={(e) => setPipeCollection(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-slate-100"
            >
              {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">Stages</span>
            <Button size="sm" variant="secondary" onClick={addStage}>
              <Plus size={14} /> Add Stage
            </Button>
          </div>
          {stages.map((s, i) => (
            <div key={i} className="flex items-center gap-2 p-3 bg-slate-800/50 rounded-lg">
              <select
                value={s.type}
                onChange={(e) => updateStage(i, { type: e.target.value })}
                className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-200"
              >
                {STAGE_TYPES.map((t) => <option key={t} value={t}>${t}</option>)}
              </select>
              <input
                value={s.params}
                onChange={(e) => updateStage(i, { params: e.target.value })}
                placeholder='{"field": "value"}'
                className="flex-1 bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm font-mono text-slate-200"
              />
              <button onClick={() => removeStage(i)} className="text-slate-600 hover:text-red-400">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowBuilder(false)}>Cancel</Button>
            <Button onClick={savePipeline}>Save Pipeline</Button>
          </div>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal open={showEdit} onClose={() => { setShowEdit(false); setEditingPipeline(null) }} title="Edit Pipeline" size="lg">
        <div className="space-y-4">
          <Input label="Pipeline Name" value={editName} onChange={(e) => setEditName(e.target.value)} />
          <div className="space-y-1.5">
            <label className="text-sm font-medium text-slate-400">Collection</label>
            <select
              value={editCollection}
              onChange={(e) => setEditCollection(e.target.value)}
              className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-slate-100"
            >
              {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
            </select>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-slate-500">Stages</span>
            <Button size="sm" variant="secondary" onClick={() => setEditStages((prev) => [...prev, { type: 'match', params: '{}' }])}>
              <Plus size={14} /> Add Stage
            </Button>
          </div>
          {editStages.map((s, i) => (
            <div key={i} className="flex items-center gap-2 p-3 bg-slate-800/50 rounded-lg">
              <select
                value={s.type}
                onChange={(e) => setEditStages((prev) => prev.map((st, j) => j === i ? { ...st, type: e.target.value } : st))}
                className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1 text-sm text-slate-200"
              >
                {STAGE_TYPES.map((t) => <option key={t} value={t}>${t}</option>)}
              </select>
              <input
                value={s.params}
                onChange={(e) => setEditStages((prev) => prev.map((st, j) => j === i ? { ...st, params: e.target.value } : st))}
                placeholder='{"field": "value"}'
                className="flex-1 bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm font-mono text-slate-200"
              />
              <button onClick={() => setEditStages((prev) => prev.filter((_, j) => j !== i))} className="text-slate-600 hover:text-red-400">
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => { setShowEdit(false); setEditingPipeline(null) }}>Cancel</Button>
            <Button onClick={saveEdit}>Save Changes</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
