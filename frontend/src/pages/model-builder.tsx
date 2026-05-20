import { useState, useCallback, useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Plus, Trash2, GripVertical, Eye, Code2,
  ArrowLeft, Sparkles, Type, Hash,
  ToggleLeft, Calendar, List, Braces, Link2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Toggle } from '@/components/ui/toggle'
import { Badge } from '@/components/ui/badge'
import { JSONEditor } from '@/components/ui/json-editor'
import { useModelStore } from '@/stores/modelStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'
import type { FieldDefinition, FieldType } from '@/types'

const FIELD_TYPES: { type: FieldType; icon: React.ReactNode; color: string }[] = [
  { type: 'string', icon: <Type size={14} />, color: 'text-blue-400 bg-blue-500/10' },
  { type: 'number', icon: <Hash size={14} />, color: 'text-emerald-400 bg-emerald-500/10' },
  { type: 'boolean', icon: <ToggleLeft size={14} />, color: 'text-purple-400 bg-purple-500/10' },
  { type: 'date', icon: <Calendar size={14} />, color: 'text-orange-400 bg-orange-500/10' },
  { type: 'array', icon: <List size={14} />, color: 'text-pink-400 bg-pink-500/10' },
  { type: 'object', icon: <Braces size={14} />, color: 'text-indigo-400 bg-indigo-500/10' },
  { type: 'relation', icon: <Link2 size={14} />, color: 'text-teal-400 bg-teal-500/10' },
]

interface FieldEditorState {
  name: string
  type: FieldType
  required: boolean
  unique: boolean
  indexed: boolean
  minLength: string
  maxLength: string
  minimum: string
  maximum: string
  pattern: string
  enum: string
  relationType: string
  targetModel: string
}

const defaultField = (): FieldEditorState => ({
  name: '',
  type: 'string',
  required: false,
  unique: false,
  indexed: false,
  minLength: '',
  maxLength: '',
  minimum: '',
  maximum: '',
  pattern: '',
  enum: '',
  relationType: 'belongs_to',
  targetModel: '',
})

export function ModelBuilderPage() {
  const navigate = useNavigate()
  const { name: editName } = useParams<{ name: string }>()
  const isEdit = !!editName
  const createModel = useModelStore((s) => s.createModel)
  const models = useModelStore((s) => s.models)
  const loadModels = useModelStore((s) => s.loadModels)
  const toast = useUIStore((s) => s.toast)

  const [modelName, setModelName] = useState(editName || '')
  const [authProtected, setAuthProtected] = useState(true)
  const [realtimeEnabled, setRealtimeEnabled] = useState(false)
  const [fields, setFields] = useState<FieldEditorState[]>([])
  const [indexes, setIndexes] = useState<{ field: string; direction: 1 | -1; unique: boolean }[]>([])
  const [selectedField, setSelectedField] = useState<number | null>(null)
  const [tab, setTab] = useState<'fields' | 'indexes' | 'preview'>('fields')
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadModels()
  }, [])

  useEffect(() => {
    if (isEdit && editName && models.length) {
      const existing = models.find((m) => m.name === editName)
      if (existing) {
        setModelName(existing.name)
        setAuthProtected(existing.auth_protected)
        setRealtimeEnabled(existing.realtime_enabled)
        setFields(
          existing.fields.map((f: any) => ({
            name: f.name,
            type: f.type,
            required: f.required || false,
            unique: f.validation?.unique || false,
            indexed: f.indexed || false,
            minLength: f.validation?.min_length?.toString() || '',
            maxLength: f.validation?.max_length?.toString() || '',
            minimum: f.validation?.minimum?.toString() || '',
            maximum: f.validation?.maximum?.toString() || '',
            pattern: f.validation?.pattern || '',
            enum: (f.validation?.enum || []).join(', '),
            relationType: f.relation?.type || 'belongs_to',
            targetModel: f.relation?.target_model || '',
          }))
        )
        setIndexes((existing.indexes || []).map((i) => ({ field: i.field, direction: i.direction, unique: i.unique || false })))
      }
    }
  }, [isEdit, editName, models])

  const addField = () => {
    setFields((prev) => [...prev, defaultField()])
    setSelectedField(fields.length)
  }

  const removeField = (idx: number) => {
    setFields((prev) => prev.filter((_, i) => i !== idx))
    setSelectedField((prev) => (prev === idx ? null : prev))
  }

  const updateField = (idx: number, updates: Partial<FieldEditorState>) => {
    setFields((prev) => prev.map((f, i) => (i === idx ? { ...f, ...updates } : f)))
  }

  const addIndex = () => {
    setIndexes((prev) => [...prev, { field: '', direction: 1, unique: false }])
  }

  const updateIndex = (idx: number, updates: Partial<{ field: string; direction: 1 | -1; unique: boolean }>) => {
    setIndexes((prev) => prev.map((i, j) => (j === idx ? { ...i, ...updates } : i)))
  }

  const removeIndex = (idx: number) => {
    setIndexes((prev) => prev.filter((_, i) => i !== idx))
  }

  const toFieldDefinition = (f: FieldEditorState): FieldDefinition => ({
    name: f.name,
    type: f.type,
    required: f.required,
    indexed: f.indexed || f.unique,
    validation: {
      required: f.required,
      unique: f.unique,
      min_length: f.minLength ? parseInt(f.minLength) : undefined,
      max_length: f.maxLength ? parseInt(f.maxLength) : undefined,
      minimum: f.minimum ? parseFloat(f.minimum) : undefined,
      maximum: f.maximum ? parseFloat(f.maximum) : undefined,
      pattern: f.pattern || undefined,
      enum: f.enum ? f.enum.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
    },
    relation: f.type === 'relation' && f.targetModel
      ? { type: f.relationType as 'belongs_to' | 'has_one' | 'has_many', target_model: f.targetModel, foreign_key: `${f.targetModel}_id` }
      : undefined,
  })

  const generatePreview = useCallback(() => {
    const schema = {
      name: modelName || 'ModelName',
      fields: fields.filter((f) => f.name).map(toFieldDefinition),
      indexes: indexes.filter((i) => i.field),
      auth_protected: authProtected,
      realtime_enabled: realtimeEnabled,
    }
    const endpoints = [
      `GET    /api/${schema.name}`,
      `POST   /api/${schema.name}`,
      `GET    /api/${schema.name}/:id`,
      `PATCH  /api/${schema.name}/:id`,
      `PUT    /api/${schema.name}/:id`,
      `DELETE /api/${schema.name}/:id`,
    ]
    return JSON.stringify(schema, null, 2) + '\n\n// Generated Endpoints:\n' + endpoints.join('\n')
  }, [modelName, fields, indexes, authProtected, realtimeEnabled])

  const handleSave = async () => {
    if (!modelName.trim()) {
      toast('Model name is required', 'error')
      return
    }
    const validFields = fields.filter((f) => f.name.trim())
    if (validFields.length === 0) {
      toast('Add at least one field', 'error')
      return
    }

    setSaving(true)
    try {
      const payload = {
        name: modelName.trim(),
        fields: validFields.map(toFieldDefinition),
        indexes: indexes.filter((i) => i.field),
        auth_protected: authProtected,
        realtime_enabled: realtimeEnabled,
      }
      if (isEdit) {
        await api.put(`/api/models/${editName}`, payload)
        toast(`✨ Model "${modelName}" updated!`, 'success')
      } else {
        await createModel(payload)
        toast(`✨ API generated for "${modelName}"!`, 'success')
      }
      navigate('/')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to save model', 'error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft size={16} />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-slate-100">{isEdit ? 'Edit Model' : 'Create Model'}</h1>
            <p className="text-sm text-slate-500 mt-1">{isEdit ? `Update "${editName}" schema` : 'Define your data schema and generate APIs instantly'}</p>
          </div>
        </div>
        <Button size="lg" loading={saving} onClick={handleSave}>
          <Sparkles size={16} />
          Generate API
        </Button>
      </div>

      {/* Model basics */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left - model info */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <Input
              label="Model Name"
              placeholder="e.g. Task, Product, User"
              value={modelName}
              onChange={(e) => setModelName(e.target.value)}
            />
            <div className="space-y-3 pt-2">
              <Toggle label="🔒 Auth Protected" checked={authProtected} onChange={setAuthProtected} />
              <Toggle label="⚡ Enable Real-time" checked={realtimeEnabled} onChange={setRealtimeEnabled} />
            </div>
          </div>

          {/* Field palette */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-5">
            <p className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-3">Field Types</p>
            <div className="grid grid-cols-2 gap-2">
              {FIELD_TYPES.map((ft) => (
                <div
                  key={ft.type}
                  className={`flex items-center gap-2 px-3 py-2 rounded-lg text-xs ${ft.color} border border-transparent hover:border-slate-600 cursor-pointer transition-all`}
                  onClick={() => {
                    addField()
                    setTimeout(() => updateField(fields.length, { type: ft.type }), 0)
                  }}
                >
                  {ft.icon}
                  {ft.type}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right - Builder */}
        <div className="lg:col-span-2 space-y-4">
          {/* Tabs */}
          <div className="flex gap-1 bg-slate-900 border border-slate-800 rounded-lg p-1">
            {(['fields', 'indexes', 'preview'] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                  tab === t ? 'bg-slate-800 text-slate-200 shadow-sm' : 'text-slate-500 hover:text-slate-300'
                }`}
              >
                {t === 'fields' ? `Fields (${fields.length})` : t === 'indexes' ? `Indexes (${indexes.length})` : 'Preview'}
              </button>
            ))}
          </div>

          {/* Fields tab */}
          {tab === 'fields' && (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
              {/* Field list */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-slate-500">Fields</span>
                  <Button size="sm" variant="secondary" onClick={addField}>
                    <Plus size={14} /> Add Field
                  </Button>
                </div>
                {fields.length === 0 ? (
                  <div className="bg-slate-900 border border-dashed border-slate-700 rounded-xl p-8 text-center">
                    <p className="text-sm text-slate-600">Click "Add Field" or select a type from the palette</p>
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[500px] overflow-y-auto pr-1">
                    {fields.map((f, i) => {
                      const ft = FIELD_TYPES.find((t) => t.type === f.type)
                      return (
                        <motion.div
                          key={i}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: i * 0.03 }}
                          onClick={() => setSelectedField(i)}
                          className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                            selectedField === i
                              ? 'bg-slate-800 border-mongodb-green/40'
                              : 'bg-slate-900 border-slate-800 hover:border-slate-600'
                          }`}
                        >
                          <GripVertical size={14} className="text-slate-600 shrink-0" />
                          <div className={`w-7 h-7 rounded-md flex items-center justify-center ${ft?.color || 'bg-slate-800'}`}>
                            {ft?.icon || <Type size={14} />}
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium text-slate-200 truncate">
                              {f.name || <span className="text-slate-600 italic">new field</span>}
                            </p>
                            <p className="text-xs text-slate-500">{f.type}{f.required ? ' · required' : ''}</p>
                          </div>
                          {f.unique && <Badge variant="info" className="text-[10px]">unique</Badge>}
                          <button
                            onClick={(e) => { e.stopPropagation(); removeField(i) }}
                            className="text-slate-600 hover:text-red-400 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </motion.div>
                      )
                    })}
                  </div>
                )}
              </div>

              {/* Field editor */}
              <div>
                {selectedField !== null && fields[selectedField] ? (
                  <motion.div
                    key={selectedField}
                    initial={{ opacity: 0, x: 20 }}
                    animate={{ opacity: 1, x: 0 }}
                    className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4"
                  >
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-slate-200">Field Settings</h3>
                      <Badge>{fields[selectedField].type}</Badge>
                    </div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="col-span-2">
                        <Input
                          label="Field Name"
                          placeholder="e.g. title, price"
                          value={fields[selectedField].name}
                          onChange={(e) => updateField(selectedField, { name: e.target.value })}
                        />
                      </div>
                      <div className="col-span-2">
                        <label className="text-sm font-medium text-slate-400 block mb-1.5">Type</label>
                        <div className="flex flex-wrap gap-1.5">
                          {FIELD_TYPES.map((ft) => (
                            <button
                              key={ft.type}
                              onClick={() => updateField(selectedField, { type: ft.type })}
                              className={`flex items-center gap-1 px-2.5 py-1.5 rounded-md text-xs border transition-all ${
                                fields[selectedField].type === ft.type
                                  ? 'border-mongodb-green bg-mongodb-green/10 text-mongodb-green'
                                  : 'border-slate-700 text-slate-400 hover:border-slate-500'
                              }`}
                            >
                              {ft.icon}
                              {ft.type}
                            </button>
                          ))}
                        </div>
                      </div>
                      <Toggle
                        label="Required"
                        checked={fields[selectedField].required}
                        onChange={(v) => updateField(selectedField, { required: v })}
                      />
                      <Toggle
                        label="Unique"
                        checked={fields[selectedField].unique}
                        onChange={(v) => updateField(selectedField, { unique: v })}
                      />
                      <Toggle
                        label="Indexed"
                        checked={fields[selectedField].indexed}
                        onChange={(v) => updateField(selectedField, { indexed: v })}
                      />
                    </div>

                    {fields[selectedField].type === 'string' && (
                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800">
                        <Input label="Min Length" type="number" placeholder="0" value={fields[selectedField].minLength} onChange={(e) => updateField(selectedField, { minLength: e.target.value })} />
                        <Input label="Max Length" type="number" placeholder="100" value={fields[selectedField].maxLength} onChange={(e) => updateField(selectedField, { maxLength: e.target.value })} />
                        <div className="col-span-2">
                          <Input label="Regex Pattern" placeholder="/^[A-Za-z]+$/" value={fields[selectedField].pattern} onChange={(e) => updateField(selectedField, { pattern: e.target.value })} />
                        </div>
                        <div className="col-span-2">
                          <Input label="Enum Values (comma-separated)" placeholder="urgent, normal, low" value={fields[selectedField].enum} onChange={(e) => updateField(selectedField, { enum: e.target.value })} />
                        </div>
                      </div>
                    )}

                    {fields[selectedField].type === 'number' && (
                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800">
                        <Input label="Minimum" type="number" value={fields[selectedField].minimum} onChange={(e) => updateField(selectedField, { minimum: e.target.value })} />
                        <Input label="Maximum" type="number" value={fields[selectedField].maximum} onChange={(e) => updateField(selectedField, { maximum: e.target.value })} />
                      </div>
                    )}

                    {fields[selectedField].type === 'relation' && (
                      <div className="grid grid-cols-2 gap-3 pt-2 border-t border-slate-800">
                        <div className="space-y-1.5">
                          <label className="text-sm font-medium text-slate-400">Relation Type</label>
                          <select
                            value={fields[selectedField].relationType}
                            onChange={(e) => updateField(selectedField, { relationType: e.target.value })}
                            className="w-full rounded-lg border border-slate-700 bg-slate-800/50 px-3 py-2 text-sm text-slate-100"
                          >
                            <option value="belongs_to">Belongs To</option>
                            <option value="has_one">Has One</option>
                            <option value="has_many">Has Many</option>
                          </select>
                        </div>
                        <Input label="Target Model" placeholder="e.g. Category" value={fields[selectedField].targetModel} onChange={(e) => updateField(selectedField, { targetModel: e.target.value })} />
                      </div>
                    )}
                  </motion.div>
                ) : (
                  <div className="bg-slate-900 border border-dashed border-slate-700 rounded-xl p-8 text-center h-full flex flex-col items-center justify-center">
                    <Code2 size={32} className="text-slate-700 mb-3" />
                    <p className="text-sm text-slate-600">Select a field to edit its settings</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Indexes tab */}
          {tab === 'indexes' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-slate-500">Database indexes improve query performance</span>
                <Button size="sm" variant="secondary" onClick={addIndex}>
                  <Plus size={14} /> Add Index
                </Button>
              </div>
              {indexes.length === 0 ? (
                <div className="text-center py-8 text-sm text-slate-600">No indexes defined. Indexes are auto-created for unique fields.</div>
              ) : (
                <div className="space-y-2">
                  {indexes.map((idx, i) => (
                    <div key={i} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                      <span className="text-sm text-slate-500 w-6">{i + 1}</span>
                      <input
                        value={idx.field}
                        onChange={(e) => updateIndex(i, { field: e.target.value })}
                        placeholder="field name"
                        className="flex-1 bg-slate-900 border border-slate-700 rounded-md px-3 py-1.5 text-sm text-slate-200"
                      />
                      <select
                        value={idx.direction}
                        onChange={(e) => updateIndex(i, { direction: parseInt(e.target.value) as 1 | -1 })}
                        className="bg-slate-900 border border-slate-700 rounded-md px-2 py-1.5 text-sm text-slate-200"
                      >
                        <option value={1}>ASC</option>
                        <option value={-1}>DESC</option>
                      </select>
                      <label className="flex items-center gap-1.5 text-xs text-slate-400">
                        <input type="checkbox" checked={idx.unique} onChange={(e) => updateIndex(i, { unique: e.target.checked })} className="rounded" />
                        unique
                      </label>
                      <button onClick={() => removeIndex(i)} className="text-slate-600 hover:text-red-400">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Preview tab */}
          {tab === 'preview' && (
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <Eye size={16} className="text-slate-500" />
                  <span className="text-sm text-slate-400">Schema Preview</span>
                </div>
              </div>
              <div className="p-1">
                <pre className="text-xs text-slate-300 font-mono leading-relaxed overflow-x-auto p-4">
                  {generatePreview()}
                </pre>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
