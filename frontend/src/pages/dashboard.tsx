import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Plus, Database, Leaf, ArrowRight, Upload } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Modal } from '@/components/ui/modal'
import { JSONEditor } from '@/components/ui/json-editor'
import { useModelStore } from '@/stores/modelStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'

export function DashboardPage() {
  const models = useModelStore((s) => s.models)
  const loadModels = useModelStore((s) => s.loadModels)
  const navigate = useNavigate()
  const toast = useUIStore((s) => s.toast)

  const [showImport, setShowImport] = useState(false)
  const [importBody, setImportBody] = useState('{\n  "name": "",\n  "fields": []\n}')
  const [importing, setImporting] = useState(false)

  useEffect(() => {
    loadModels()
  }, [loadModels])

  const handleImport = async () => {
    setImporting(true)
    try {
      const schema = JSON.parse(importBody)
      await api.post('/api/models/import', schema)
      toast('Model imported', 'success')
      setShowImport(false)
      loadModels()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Import failed', 'error')
    } finally { setImporting(false) }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-slate-100">Collections</h1>
          <p className="text-sm text-slate-500 mt-1">
            {models.length} model{models.length !== 1 ? 's' : ''} defined
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => setShowImport(true)}>
            <Upload size={16} />
            Import
          </Button>
          <Button onClick={() => navigate('/models/new')}>
            <Plus size={16} />
            New Model
          </Button>
        </div>
      </div>

      {/* Empty state */}
      {models.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col items-center justify-center py-24 text-center"
        >
          <div className="w-16 h-16 rounded-2xl bg-mongodb-green/10 flex items-center justify-center mb-6 border border-mongodb-green/20">
            <Database size={32} className="text-mongodb-green" />
          </div>
          <h2 className="text-xl font-semibold text-slate-200 mb-2">No models yet</h2>
          <p className="text-slate-500 max-w-md mb-8">
            Create your first model to instantly generate REST APIs with authentication, filtering, and real-time support.
          </p>
          <Button size="lg" onClick={() => navigate('/models/new')}>
            <Leaf size={18} />
            Create Your First Model
          </Button>
        </motion.div>
      ) : (
        /* Model grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {models.map((model, i) => (
            <motion.div
              key={model._id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05 }}
              onClick={() => navigate(`/models/${model.name}`)}
              className="group cursor-pointer bg-slate-900 border border-slate-800 rounded-xl p-5 hover:border-mongodb-green/40 hover:shadow-lg hover:shadow-mongodb-green/5 transition-all duration-300"
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 rounded-lg bg-mongodb-green/10 flex items-center justify-center border border-mongodb-green/20">
                  <Database size={18} className="text-mongodb-green" />
                </div>
                <ArrowRight size={16} className="text-slate-600 group-hover:text-mongodb-green transition-colors opacity-0 group-hover:opacity-100" />
              </div>
              <h3 className="font-semibold text-slate-200 mb-1 group-hover:text-mongodb-green transition-colors">
                {model.name}
              </h3>
              <p className="text-sm text-slate-500 mb-3">
                {model.fields.length} field{model.fields.length !== 1 ? 's' : ''}
                {model.indexes?.length ? ` · ${model.indexes.length} index${model.indexes.length !== 1 ? 'es' : ''}` : ''}
              </p>
              <div className="flex gap-1.5">
                {model.auth_protected && <Badge variant="purple">🔒 Auth</Badge>}
                {model.realtime_enabled && <Badge variant="success">⚡ Live</Badge>}
              </div>
            </motion.div>
          ))}

          {/* New model card */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: models.length * 0.05 }}
            onClick={() => navigate('/models/new')}
            className="cursor-pointer bg-slate-900/50 border border-dashed border-slate-700 rounded-xl p-5 flex flex-col items-center justify-center min-h-[160px] hover:border-mongodb-green/40 hover:bg-slate-900/80 transition-all duration-300"
          >
            <Plus size={24} className="text-slate-600 mb-2" />
            <span className="text-sm text-slate-500 font-medium">Create New Model</span>
          </motion.div>
        </div>
      )}

      <Modal open={showImport} onClose={() => setShowImport(false)} title="Import Model" size="lg">
        <div className="space-y-4">
          <p className="text-sm text-slate-500">Paste a model schema JSON to import</p>
          <JSONEditor value={importBody} onChange={setImportBody} height="300px" />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setShowImport(false)}>Cancel</Button>
            <Button loading={importing} onClick={handleImport}>Import Model</Button>
          </div>
        </div>
      </Modal>
    </div>
  )
}
