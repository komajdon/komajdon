import { useEffect, useState, useCallback } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  ArrowLeft, Code2, Play, PieChart, Download, Copy, Wifi, Trash2, Edit3,
  Cpu,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { JSONEditor } from '@/components/ui/json-editor'
import { useModelStore } from '@/stores/modelStore'
import { useUIStore } from '@/stores/uiStore'
import { useRealtime } from '@/hooks/useRealtime'
import { api } from '@/services/api'
import { cn, getMethodBadgeClass } from '@/lib/utils'
import type { ModelSchema, ApiEndpoint } from '@/types'

type Tab = 'schema' | 'playground' | 'aggregations' | 'sdk' | 'realtime'

export function ModelDetailPage() {
  const { name } = useParams<{ name: string }>()
  const navigate = useNavigate()
  const models = useModelStore((s) => s.models)
  const deleteModel = useModelStore((s) => s.deleteModel)
  const loadModels = useModelStore((s) => s.loadModels)
  const toast = useUIStore((s) => s.toast)
  const [tab, setTab] = useState<Tab>('schema')

  const model = models.find((m) => m.name === name)

  useEffect(() => {
    if (!models.length) loadModels()
  }, [loadModels])

  useEffect(() => {
    if (models.length > 0 && !model) {
      navigate('/')
    }
  }, [models, model, navigate])

  const handleDelete = async () => {
    if (!model || !confirm(`Delete "${model.name}"? All data will be lost.`)) return
    try {
      await deleteModel(model.name)
      toast(`Model "${model.name}" deleted`, 'info')
      navigate('/')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    }
  }

  if (!model) return null

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'schema', label: 'Schema', icon: <Code2 size={14} /> },
    { key: 'playground', label: 'Playground', icon: <Play size={14} /> },
    { key: 'aggregations', label: 'Aggregations', icon: <PieChart size={14} /> },
    { key: 'sdk', label: 'SDK', icon: <Cpu size={14} /> },
    { key: 'realtime', label: 'Real-time', icon: <Wifi size={14} /> },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-slate-100">{model.name}</h1>
              <div className="flex gap-1">
                {model.auth_protected && <Badge variant="purple">🔒 Auth</Badge>}
                {model.realtime_enabled && <Badge variant="success">⚡ Live</Badge>}
              </div>
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {model.fields.length} fields · {model.indexes?.length || 0} indexes
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => navigate(`/models/${model.name}/edit`)}>
            <Edit3 size={14} /> Edit
          </Button>
          <Button variant="danger" size="sm" onClick={handleDelete}>
            <Trash2 size={14} /> Delete
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={cn(
              'flex items-center gap-1.5 px-4 py-2 text-sm font-medium rounded-md transition-all',
              tab === t.key
                ? 'bg-slate-800 text-slate-200 shadow-sm'
                : 'text-slate-500 hover:text-slate-300'
            )}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <motion.div key={tab} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.2 }}>
        {tab === 'schema' && <SchemaTab model={model} />}
        {tab === 'playground' && <PlaygroundTab model={model} />}
        {tab === 'aggregations' && <AggregationsTab model={model} />}
        {tab === 'sdk' && <SDKTab model={model} />}
        {tab === 'realtime' && <RealtimeTab model={model} />}
      </motion.div>
    </div>
  )
}

function SchemaTab({ model }: { model: ModelSchema }) {
  const toast = useUIStore((s) => s.toast)
  const exportSchema = async () => {
    try {
      const data = await api.get(`/api/models/${model.name}/export`)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = `${model.name}-schema.json`
      a.click()
    } catch {
      toast('Export failed', 'error')
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Fields */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-200">Fields</h3>
          <Button size="sm" variant="secondary" onClick={exportSchema}>
            <Download size={14} /> Export
          </Button>
        </div>
        {model.fields.length === 0 ? (
          <p className="text-sm text-slate-600">No fields defined</p>
        ) : (
          <div className="grid grid-cols-1 gap-2">
            {model.fields.map((f, i) => (
              <motion.div
                key={f.name}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.03 }}
                className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg"
              >
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-slate-200">{f.name}</span>
                    <span className="text-xs text-slate-500">{f.type}</span>
                  </div>
                  <div className="flex gap-1 mt-1 flex-wrap">
                    {f.required && <Badge variant="info" className="text-[10px]">req</Badge>}
                    {f.validation?.unique && <Badge variant="info" className="text-[10px]">unique</Badge>}
                    {f.indexed && <Badge variant="info" className="text-[10px]">indexed</Badge>}
                    {f.validation?.enum?.length && <Badge variant="info" className="text-[10px]">enum</Badge>}
                    {f.relation && <Badge variant="purple" className="text-[10px]">→ {f.relation.target_model}</Badge>}
                  </div>
                  {f.validation?.pattern && <p className="text-[10px] text-slate-600 mt-1 font-mono">{f.validation.pattern}</p>}
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* JSON + Indexes */}
      <div className="space-y-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold text-slate-200">JSON Schema</h3>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => {
                navigator.clipboard.writeText(JSON.stringify(model, null, 2))
                toast('Copied!', 'success')
              }}
            >
              <Copy size={14} />
            </Button>
          </div>
          <pre className="text-xs text-slate-400 font-mono leading-relaxed overflow-x-auto max-h-64">
            {JSON.stringify(model, null, 2)}
          </pre>
        </div>
        {model.indexes?.length > 0 && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <h3 className="font-semibold text-slate-200 mb-3">Indexes</h3>
            <div className="flex flex-wrap gap-2">
              {model.indexes.map((idx, i) => (
                <span key={i} className="px-3 py-1.5 bg-slate-800 rounded-lg text-xs text-slate-400 font-mono border border-slate-700">
                  {idx.field} ({idx.direction === 1 ? 'ASC' : 'DESC'}){idx.unique ? ' · unique' : ''}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function PlaygroundTab({ model }: { model: ModelSchema }) {
  const endpoints: ApiEndpoint[] = [
    { method: 'GET', path: `/api/${model.name}`, desc: 'List', hasQuery: true },
    { method: 'POST', path: `/api/${model.name}`, desc: 'Create', hasBody: true },
    { method: 'GET', path: `/api/${model.name}/:id`, desc: 'Get by ID' },
    { method: 'PATCH', path: `/api/${model.name}/:id`, desc: 'Update', hasBody: true },
    { method: 'PUT', path: `/api/${model.name}/:id`, desc: 'Replace', hasBody: true },
    { method: 'DELETE', path: `/api/${model.name}/:id`, desc: 'Delete' },
  ]
  const [response, setResponse] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const toast = useUIStore((s) => s.toast)

  const handleTest = useCallback(async (ep: ApiEndpoint) => {
    const id = ep.path.includes(':id') ? prompt('Enter document ID:') : null
    if (ep.path.includes(':id') && !id) return

    const exampleBody = ep.hasBody ? model.fields.reduce((acc, f) => {
      if (f.type === 'string') acc[f.name] = 'example'
      else if (f.type === 'number') acc[f.name] = 0
      else if (f.type === 'boolean') acc[f.name] = false
      else if (f.type === 'date') acc[f.name] = new Date().toISOString()
      else acc[f.name] = null
      return acc
    }, {} as Record<string, unknown>) : undefined

    const body = ep.hasBody ? prompt('Request body (JSON):', JSON.stringify(exampleBody, null, 2)) : null
    if (ep.hasBody && !body) return

    setLoading(true)
    setResponse(null)
    try {
      let path = `/api/${model.name}`
      if (id) path += `/${id}`
      const data = await api.request(ep.method, path, body ? JSON.parse(body) : undefined)
      setResponse(JSON.stringify(data, null, 2))
    } catch (e: unknown) {
      setResponse(`Error: ${e instanceof Error ? e.message : 'Request failed'}`)
    } finally {
      setLoading(false)
    }
  }, [model])

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-2">
        <h3 className="font-semibold text-slate-200 mb-3">Endpoints</h3>
        {endpoints.map((ep) => (
          <div key={`${ep.method}-${ep.path}`} className="flex items-center gap-3 p-3 bg-slate-800/30 rounded-lg hover:bg-slate-800/50 transition-colors">
            <span className={`text-xs font-bold px-2 py-0.5 rounded ${getMethodBadgeClass(ep.method)}`}>
              {ep.method}
            </span>
            <span className="flex-1 text-sm font-mono text-slate-300">{ep.path}</span>
            <Button size="sm" variant="ghost" loading={loading} onClick={() => handleTest(ep)}>
              <Play size={12} /> Test
            </Button>
          </div>
        ))}
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="font-semibold text-slate-200 mb-3">Response</h3>
        <pre className="text-xs text-slate-400 font-mono leading-relaxed overflow-x-auto max-h-96">
          {response || '// Send a request to see the response'}
        </pre>
      </div>
    </div>
  )
}

function AggregationsTab({ model }: { model: ModelSchema }) {
  const [result, setResult] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState<{ id: string; name: string }[]>([])
  const [fieldName, setFieldName] = useState('')
  const [valueField, setValueField] = useState('')

  useEffect(() => {
    api.get<{ id: string; name: string }[]>('/api/aggregations/templates').then(setTemplates).catch(() => {})
  }, [])

  const runTemplate = async (template: string) => {
    setLoading(true)
    setResult(null)
    try {
      let path = `/api/aggregations/run/${model.name}?template=${template}`
      if (fieldName) path += `&field_name=${encodeURIComponent(fieldName)}`
      if (valueField) path += `&value_field=${encodeURIComponent(valueField)}`
      const data = await api.post(path)
      setResult(JSON.stringify(data, null, 2))
    } catch (e: unknown) {
      setResult(`Error: ${e instanceof Error ? e.message : 'Failed'}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
          <h3 className="font-semibold text-slate-200">Aggregation Templates</h3>
          <div className="grid grid-cols-2 gap-3">
            {templates.map((t) => (
              <button
                key={t.id}
                onClick={() => runTemplate(t.id)}
                disabled={loading}
                className="p-4 bg-slate-800/50 rounded-lg border border-slate-700 hover:border-accent-purple/40 text-left transition-all hover:bg-slate-800"
              >
                <p className="text-sm font-medium text-slate-200">{t.name}</p>
              </button>
            ))}
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Input label="Field Name" placeholder="e.g. status" value={fieldName} onChange={(e) => setFieldName(e.target.value)} />
            <Input label="Value Field" placeholder="e.g. price" value={valueField} onChange={(e) => setValueField(e.target.value)} />
          </div>
        </div>
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="font-semibold text-slate-200 mb-3">Results</h3>
        <pre className="text-xs text-slate-400 font-mono leading-relaxed overflow-x-auto max-h-96">
          {loading ? '⏳ Running...' : result || '// Select a template to run'}
        </pre>
      </div>
    </div>
  )
}

function SDKTab({ model }: { model: ModelSchema }) {
  const [lang, setLang] = useState<'typescript' | 'python'>('typescript')
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(true)
  const toast = useUIStore((s) => s.toast)

  useEffect(() => {
    setLoading(true)
    api.get<string>(`/api/sdk/${model.name}?lang=${lang}`)
      .then(setCode)
      .catch((e) => setCode(`Error: ${e.message}`))
      .finally(() => setLoading(false))
  }, [model.name, lang])

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex gap-2">
          <button
            onClick={() => setLang('typescript')}
            className={`px-3 py-1.5 text-sm rounded-md transition-all ${lang === 'typescript' ? 'bg-slate-800 text-slate-200' : 'text-slate-500 hover:text-slate-300'}`}
          >
            TypeScript
          </button>
          <button
            onClick={() => setLang('python')}
            className={`px-3 py-1.5 text-sm rounded-md transition-all ${lang === 'python' ? 'bg-slate-800 text-slate-200' : 'text-slate-500 hover:text-slate-300'}`}
          >
            Python
          </button>
        </div>
        <Button size="sm" variant="ghost" onClick={() => { navigator.clipboard.writeText(code); toast('Copied!') }}>
          <Copy size={14} /> Copy
        </Button>
      </div>
      <pre className="text-xs text-slate-300 font-mono leading-relaxed overflow-x-auto p-5 max-h-96">
        {loading ? '⏳ Generating...' : code}
      </pre>
    </div>
  )
}

function RealtimeTab({ model }: { model: ModelSchema }) {
  const { connected, events, clear } = useRealtime(model.realtime_enabled ? model.name : null)

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="font-semibold text-slate-200">Connection</h3>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${connected ? 'bg-emerald-500 animate-pulse' : 'bg-red-500'}`} />
            <span className="text-sm text-slate-400">{connected ? 'Connected' : 'Disconnected'}</span>
          </div>
        </div>
        {!model.realtime_enabled && (
          <p className="text-sm text-amber-400 bg-amber-500/10 p-3 rounded-lg">
            Real-time is not enabled for this model. Toggle it in the model settings.
          </p>
        )}
        {model.realtime_enabled && (
          <Input
            label="WebSocket URL"
            value={`ws://localhost:8000/ws/${model.name}?token=<your-auth-token>`}
            readOnly
            className="font-mono text-xs"
          />
        )}
        {connected && (
          <Button size="sm" variant="secondary" onClick={clear}>
            Clear Log
          </Button>
        )}
      </div>
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
        <h3 className="font-semibold text-slate-200 mb-3">Events</h3>
        <pre className="text-xs font-mono leading-relaxed max-h-64 overflow-y-auto space-y-1">
          {events.length === 0 ? (
            <span className="text-slate-600">// No events yet</span>
          ) : (
            events.slice().reverse().map((e, i) => (
              <div key={i} className="border-b border-slate-800 pb-1 mb-1">
                <span className={cn(
                  'text-[10px] font-semibold uppercase px-1 rounded',
                  e.event === 'create' ? 'text-emerald-400' :
                  e.event === 'update' ? 'text-yellow-400' :
                  e.event === 'delete' ? 'text-red-400' : 'text-slate-500'
                )}>
                  {e.event}
                </span>
                <span className="text-slate-600 ml-2">[{new Date(e.ts).toLocaleTimeString()}]</span>
                <pre className="text-slate-400 mt-1">{JSON.stringify(e.data, null, 2)}</pre>
              </div>
            ))
          )}
        </pre>
      </div>
    </div>
  )
}
