import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Plus, Trash2, Play, GripVertical,
  Globe, Shuffle, Combine, Cpu,
  Copy,
} from 'lucide-react'
import { Search } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { Badge } from '@/components/ui/badge'
import { JSONEditor } from '@/components/ui/json-editor'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'
import { getMethodBadgeClass } from '@/lib/utils'
import { useModelStore } from '@/stores/modelStore'

interface Step {
  id: string
  label: string
  type: 'request' | 'transform' | 'merge'
  method: string
  path: string
  source_steps: string[]
  transform_rules: TransformRule[]
  merge_mode: 'concat' | 'object' | 'zip'
  headers: Record<string, string>
  body: Record<string, unknown>
}

interface TransformRule {
  op: 'pick' | 'omit' | 'rename' | 'compute' | 'filter' | 'sort'
  params: Record<string, unknown>
}

interface Composition {
  _id: string
  name: string
  description: string
  method: string
  steps: Step[]
  output_step: string
  created_at: string
}

let stepCounter = 0
function newStepId() {
  stepCounter += 1
  return `step${stepCounter}`
}

export function ApiComposerPage() {
  const navigate = useNavigate()
  const toast = useUIStore((s) => s.toast)
  const models = useModelStore((s) => s.models)
  const loadModels = useModelStore((s) => s.loadModels)
  const [compositions, setCompositions] = useState<Composition[]>([])
  const [loading, setLoading] = useState(true)
  const [showBuilder, setShowBuilder] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [testing, setTesting] = useState<string | null>(null)

  // Builder state
  const [compName, setCompName] = useState('')
  const [compDesc, setCompDesc] = useState('')
  const [compMethod, setCompMethod] = useState('GET')
  const [steps, setSteps] = useState<Step[]>([])
  const [outputStep, setOutputStep] = useState('')

  // Available endpoints for request step selector
  const [availableEndpoints, setAvailableEndpoints] = useState<{ method: string; path: string; group: string; label: string }[]>([])
  const [endpointSearch, setEndpointSearch] = useState('')
  const [showEndpointPicker, setShowEndpointPicker] = useState<number | null>(null)

  useEffect(() => {
    loadModels()
    loadCompositions()
    loadEndpoints()
  }, [])

  const loadEndpoints = async () => {
    try {
      const eps = await api.get<{ method: string; path: string; group: string; label: string }[]>('/api/discover/')
      setAvailableEndpoints(eps)
    } catch {
      // ignore
    }
  }

  const loadCompositions = async () => {
    setLoading(true)
    try {
      const data = await api.get<Composition[]>('/api/compositions/')
      setCompositions(data)
    } catch {
      setCompositions([])
    } finally {
      setLoading(false)
    }
  }

  const addStep = (type: Step['type']) => {
    const id = newStepId()
    const step: Step = {
      id, label: '', type,
      method: 'GET', path: '', source_steps: [],
      transform_rules: [], merge_mode: 'concat',
      headers: {}, body: {},
    }
    setSteps((prev) => [...prev, step])
    if (!outputStep) setOutputStep(id)
  }

  const updateStep = (idx: number, updates: Partial<Step>) => {
    setSteps((prev) => prev.map((s, i) => (i === idx ? { ...s, ...updates } : s)))
  }

  const removeStep = (idx: number) => {
    const removed = steps[idx]
    setSteps((prev) => prev.filter((_, i) => i !== idx))
    if (outputStep === removed.id) {
      const remaining = steps.filter((_, i) => i !== idx)
      setOutputStep(remaining[remaining.length - 1]?.id || '')
    }
  }

  const addTransformRule = (stepIdx: number) => {
    const rule: TransformRule = { op: 'pick', params: { keys: [] } }
    updateStep(stepIdx, {
      transform_rules: [...steps[stepIdx].transform_rules, rule],
    })
  }

  const updateTransformRule = (stepIdx: number, ruleIdx: number, updates: Partial<TransformRule>) => {
    const rules = [...steps[stepIdx].transform_rules]
    rules[ruleIdx] = { ...rules[ruleIdx], ...updates }
    updateStep(stepIdx, { transform_rules: rules })
  }

  const removeTransformRule = (stepIdx: number, ruleIdx: number) => {
    const rules = steps[stepIdx].transform_rules.filter((_, i) => i !== ruleIdx)
    updateStep(stepIdx, { transform_rules: rules })
  }

  const [editingCompName, setEditingCompName] = useState<string | null>(null)

  const openBuilderForEdit = (comp: Composition) => {
    setEditingCompName(comp.name)
    setCompName(comp.name)
    setCompDesc(comp.description)
    setCompMethod(comp.method)
    setSteps(comp.steps.map(s => ({
      ...s,
      body: s.body || {},
      headers: s.headers || {},
      transform_rules: s.transform_rules || [],
      source_steps: s.source_steps || [],
      merge_mode: s.merge_mode || 'concat',
    })))
    setOutputStep(comp.output_step)
    stepCounter = comp.steps.length
    setShowBuilder(true)
  }

  const saveComposition = async () => {
    if (!compName.trim()) {
      toast('Composition name is required', 'error')
      return
    }
    if (steps.length === 0) {
      toast('Add at least one step', 'error')
      return
    }
    const payload = {
      name: compName.trim(),
      description: compDesc,
      method: compMethod,
      steps: steps.map((s) => ({
        ...s,
        transform_rules: s.transform_rules.map((r) => ({
          op: r.op,
          params: typeof r.params === 'string' ? JSON.parse(r.params) : r.params,
        })),
      })),
      output_step: outputStep,
    }
    try {
      if (editingCompName) {
        await api.put(`/api/compositions/${editingCompName}`, payload)
        toast(`Composition "${compName}" updated`, 'success')
      } else {
        await api.post('/api/compositions/', payload)
        toast(`Composition "${compName}" created at /api/composed/${compName}`, 'success')
      }
      setShowBuilder(false)
      setEditingCompName(null)
      loadCompositions()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Save failed', 'error')
    }
  }

  const testComposition = async (name: string) => {
    setTesting(name)
    setTestResult(null)
    try {
      const data = await api.get(`/api/composed/${name}`)
      setTestResult(JSON.stringify(data, null, 2))
    } catch (e: unknown) {
      setTestResult(`Error: ${e instanceof Error ? e.message : 'Request failed'}`)
    } finally {
      setTesting(null)
    }
  }

  const deleteComposition = async (name: string) => {
    if (!confirm(`Delete composition "${name}"?`)) return
    try {
      await api.delete(`/api/compositions/${name}`)
      toast('Deleted', 'info')
      loadCompositions()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    }
  }

  const stepIcons: Record<string, React.ReactNode> = {
    request: <Globe size={14} />,
    transform: <Shuffle size={14} />,
    merge: <Combine size={14} />,
  }

  const stepColors: Record<string, string> = {
    request: 'text-blue-400 bg-blue-500/10 border-blue-500/30',
    transform: 'text-purple-400 bg-purple-500/10 border-purple-500/30',
    merge: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
  }

  // ── Test result modal ──
  const [showResult, setShowResult] = useState(false)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">API Composer</h1>
            <p className="text-sm text-slate-500 mt-1">Chain, transform, and merge generated APIs into new endpoints</p>
          </div>
        </div>
        <Button onClick={() => { setCompName(''); setCompDesc(''); setSteps([]); setOutputStep(''); stepCounter = 0; setShowBuilder(true) }}>
          <Plus size={16} /> New Composition
        </Button>
      </div>

      {/* Compositions list */}
      {compositions.length === 0 && !loading ? (
        <div className="text-center py-24">
          <div className="w-16 h-16 rounded-2xl bg-purple-500/10 flex items-center justify-center mb-6 mx-auto border border-purple-500/20">
            <Cpu size={32} className="text-purple-400" />
          </div>
          <h2 className="text-xl font-semibold text-slate-200 mb-2">No composed APIs yet</h2>
          <p className="text-slate-500 max-w-md mx-auto mb-8">
            Create a composition that chains API calls, transforms data, and merges results into a single endpoint.
          </p>
          <Button onClick={() => { setCompName(''); setSteps([]); setOutputStep(''); stepCounter = 0; setShowBuilder(true) }}>
            Create Your First Composition
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          {compositions.map((comp, i) => (
            <motion.div
              key={comp._id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              className="bg-slate-900 border border-slate-800 rounded-xl p-5"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3">
                    <Badge variant="purple" className="text-[10px] font-mono">{comp.method}</Badge>
                    <h3 className="font-semibold text-slate-200">{comp.name}</h3>
                    {comp.description && (
                      <span className="text-sm text-slate-500">— {comp.description}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-3">
                    <code className="text-xs text-slate-400 font-mono bg-slate-800 px-2 py-1 rounded">
                      /api/composed/{comp.name}
                    </code>
                    <button
                      onClick={() => { navigator.clipboard.writeText(`/api/composed/${comp.name}`); toast('Copied!') }}
                      className="text-slate-600 hover:text-slate-300"
                    >
                      <Copy size={12} />
                    </button>
                  </div>
                  <div className="flex gap-1.5 mt-3">
                    {comp.steps.map((s, si) => (
                      <span
                        key={si}
                        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] border ${stepColors[s.type] || 'text-slate-400 bg-slate-800'}`}
                      >
                        {stepIcons[s.type] || <Cpu size={10} />}
                        {s.label || s.type}
                      </span>
                    ))}
                    {comp.output_step && (
                      <Badge variant="info" className="text-[10px]">→ {comp.output_step}</Badge>
                    )}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" variant="secondary" onClick={() => openBuilderForEdit(comp)}>
                    Edit
                  </Button>
                  <Button size="sm" loading={testing === comp.name} onClick={() => testComposition(comp.name)}>
                    <Play size={12} /> Test
                  </Button>
                  <Button size="sm" variant="danger" onClick={() => deleteComposition(comp.name)}>
                    <Trash2 size={12} />
                  </Button>
                </div>
              </div>
              {testResult && testing !== comp.name && (
                <pre className="mt-3 text-xs text-slate-400 font-mono bg-slate-800/50 p-3 rounded-lg max-h-40 overflow-y-auto">
                  {testResult}
                </pre>
              )}
            </motion.div>
          ))}
        </div>
      )}

      {/* ── Builder Modal ── */}
      <Modal open={showBuilder} onClose={() => setShowBuilder(false)} title="New API Composition" size="xl">
        <div className="space-y-6">
          {/* Basic info */}
          <div className="grid grid-cols-3 gap-4">
            <Input label="Composition Name" value={compName} onChange={(e) => setCompName(e.target.value)} placeholder="e.g. products-with-categories" />
            <Input label="Description" value={compDesc} onChange={(e) => setCompDesc(e.target.value)} placeholder="Optional description" />
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-400">HTTP Method</label>
              <select value={compMethod} onChange={(e) => setCompMethod(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-slate-100">
                <option value="GET">GET</option>
                <option value="POST">POST</option>
              </select>
            </div>
          </div>

          {/* Step type buttons */}
          <div className="flex gap-2">
            <Button size="sm" variant="secondary" onClick={() => addStep('request')}>
              <Globe size={14} /> + Request Step
            </Button>
            <Button size="sm" variant="secondary" onClick={() => addStep('transform')}>
              <Shuffle size={14} /> + Transform Step
            </Button>
            <Button size="sm" variant="secondary" onClick={() => addStep('merge')}>
              <Combine size={14} /> + Merge Step
            </Button>
          </div>

          {/* Steps */}
          {steps.length === 0 ? (
            <div className="text-center py-8 text-sm text-slate-600 border border-dashed border-slate-700 rounded-lg">
              Add steps to define your API composition pipeline
            </div>
          ) : (
            <div className="space-y-3">
              {steps.map((step, idx) => (
                <motion.div
                  key={step.id}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`p-4 rounded-xl border ${stepColors[step.type] || 'border-slate-700'} bg-slate-900/80`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <GripVertical size={14} className="text-slate-600 shrink-0" />
                    <span className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${stepColors[step.type]}`}>
                      {step.type}
                    </span>
                    <Input
                      value={step.label}
                      onChange={(e) => updateStep(idx, { label: e.target.value })}
                      placeholder="Step label"
                      className="!w-48"
                    />
                    <span className="text-xs text-slate-600 font-mono">{step.id}</span>
                    <div className="flex-1" />
                    <Button size="sm" variant="ghost" onClick={() => removeStep(idx)}>
                      <Trash2 size={12} className="text-red-400" />
                    </Button>
                  </div>

                  {/* Request step config */}
                  {step.type === 'request' && (
                    <div className="ml-7 space-y-3">
                      <div className="flex gap-2">
                        <select value={step.method} onChange={(e) => updateStep(idx, { method: e.target.value })}
                          className="bg-slate-800 border border-slate-700 rounded-md px-2 py-1.5 text-xs text-slate-200 w-20">
                          <option value="GET">GET</option>
                          <option value="POST">POST</option>
                        </select>
                        <div className="relative flex-1">
                          <input
                            value={step.path}
                            onChange={(e) => updateStep(idx, { path: e.target.value })}
                            placeholder="/api/products?limit=5"
                            className="w-full bg-slate-800 border border-slate-700 rounded-md px-3 py-1.5 text-xs font-mono text-slate-200 focus:border-mongodb-green focus:outline-none"
                            onFocus={() => setShowEndpointPicker(idx)}
                          />
                          <button
                            onClick={() => setShowEndpointPicker(showEndpointPicker === idx ? null : idx)}
                            className="absolute right-1.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                          >
                            <Search size={12} />
                          </button>
                        </div>
                      </div>

                      {/* Endpoint picker dropdown */}
                      {showEndpointPicker === idx && (
                        <div className="bg-slate-800 border border-slate-700 rounded-lg overflow-hidden shadow-xl max-h-52">
                          <div className="p-2 border-b border-slate-700">
                            <input
                              value={endpointSearch}
                              onChange={(e) => setEndpointSearch(e.target.value)}
                              placeholder="Search endpoints..."
                              className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 focus:border-mongodb-green focus:outline-none"
                              autoFocus
                            />
                          </div>
                          <div className="overflow-y-auto max-h-40 divide-y divide-slate-700/50">
                            {availableEndpoints
                              .filter((ep) => {
                                const q = endpointSearch.toLowerCase()
                                return !q || ep.path.toLowerCase().includes(q) || ep.label.toLowerCase().includes(q) || ep.group.toLowerCase().includes(q)
                              })
                              .map((ep, ei) => (
                                <button
                                  key={ei}
                                  onClick={() => {
                                    updateStep(idx, { method: ep.method, path: ep.path })
                                    setShowEndpointPicker(null)
                                    setEndpointSearch('')
                                  }}
                                  className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-slate-700/50 transition-colors"
                                >
                                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 ${getMethodBadgeClass(ep.method)}`}>{ep.method}</span>
                                  <span className="text-xs font-mono text-slate-300 truncate flex-1">{ep.path}</span>
                                  <span className="text-[10px] text-slate-600 shrink-0">{ep.group.split('/')[0]}</span>
                                </button>
                              ))}
                            {availableEndpoints.filter((ep) => {
                              const q = endpointSearch.toLowerCase()
                              return !q || ep.path.toLowerCase().includes(q) || ep.label.toLowerCase().includes(q) || ep.group.toLowerCase().includes(q)
                            }).length === 0 && (
                              <div className="px-3 py-4 text-xs text-slate-600 text-center">No matching endpoints</div>
                            )}
                          </div>
                        </div>
                      )}

                      <div className="text-xs text-slate-600">
                        Use {'{{step_id.field}}'} to reference previous step outputs
                      </div>
                    </div>
                  )}

                  {/* Transform step config */}
                  {step.type === 'transform' && (
                    <div className="ml-7 space-y-3">
                      <div className="flex flex-wrap gap-2">
                        {steps.filter((_, i) => i < idx).map((s) => (
                          <label key={s.id} className="flex items-center gap-1.5 text-xs text-slate-400">
                            <input
                              type="checkbox"
                              checked={step.source_steps.includes(s.id)}
                              onChange={(e) => {
                                const sources = e.target.checked
                                  ? [...step.source_steps, s.id]
                                  : step.source_steps.filter((id) => id !== s.id)
                                updateStep(idx, { source_steps: sources })
                              }}
                              className="rounded"
                            />
                            {s.label || s.id}
                          </label>
                        ))}
                      </div>

                      {/* Transform rules */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs text-slate-500">Transform Rules</span>
                          <Button size="sm" variant="ghost" onClick={() => addTransformRule(idx)}>
                            <Plus size={12} /> Add Rule
                          </Button>
                        </div>
                        {step.transform_rules.map((rule, ri) => (
                          <div key={ri} className="flex items-center gap-2 p-2 bg-slate-800/50 rounded-lg">
                            <select
                              value={rule.op}
                              onChange={(e) => updateTransformRule(idx, ri, { op: e.target.value as TransformRule['op'] })}
                              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs text-slate-200"
                            >
                              <option value="pick">pick</option>
                              <option value="omit">omit</option>
                              <option value="rename">rename</option>
                              <option value="compute">compute</option>
                              <option value="filter">filter</option>
                              <option value="sort">sort</option>
                            </select>
                            <input
                              value={typeof rule.params === 'string' ? rule.params : JSON.stringify(rule.params)}
                              onChange={(e) => updateTransformRule(idx, ri, { params: e.target.value as unknown as Record<string, unknown> })}
                              placeholder='{"keys": ["name"]}'
                              className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs font-mono text-slate-200"
                            />
                            <button onClick={() => removeTransformRule(idx, ri)} className="text-slate-600 hover:text-red-400">
                              <Trash2 size={12} />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Merge step config */}
                  {step.type === 'merge' && (
                    <div className="ml-7 space-y-3">
                      <div className="flex flex-wrap gap-2">
                        {steps.filter((_, i) => i < idx).map((s) => (
                          <label key={s.id} className="flex items-center gap-1.5 text-xs text-slate-400">
                            <input
                              type="checkbox"
                              checked={step.source_steps.includes(s.id)}
                              onChange={(e) => {
                                const sources = e.target.checked
                                  ? [...step.source_steps, s.id]
                                  : step.source_steps.filter((id) => id !== s.id)
                                updateStep(idx, { source_steps: sources })
                              }}
                              className="rounded"
                            />
                            {s.label || s.id}
                          </label>
                        ))}
                      </div>
                      <select
                        value={step.merge_mode}
                        onChange={(e) => updateStep(idx, { merge_mode: e.target.value as Step['merge_mode'] })}
                        className="bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200"
                      >
                        <option value="concat">Concatenate arrays</option>
                        <option value="object">Merge into object</option>
                        <option value="zip">Zip arrays</option>
                      </select>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          )}

          {/* Output step selector */}
          {steps.length > 0 && (
            <div className="space-y-1.5">
              <label className="text-sm font-medium text-slate-400">Output Step</label>
              <select
                value={outputStep}
                onChange={(e) => setOutputStep(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-slate-100"
              >
                {steps.map((s) => (
                  <option key={s.id} value={s.id}>{s.label || s.id} ({s.type})</option>
                ))}
              </select>
              <p className="text-xs text-slate-600">
                The endpoint will return the result of this step. The generated URL will be <code className="text-slate-400">/api/composed/{compName || 'your-name'}</code>.
              </p>
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <Button variant="secondary" onClick={() => setShowBuilder(false)}>Cancel</Button>
            <Button onClick={saveComposition}>Save Composition</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
