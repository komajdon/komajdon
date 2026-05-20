import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  RefreshCw, Plus, ChevronLeft, ChevronRight,
  ArrowLeft, Trash2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { Badge } from '@/components/ui/badge'
import { JSONEditor } from '@/components/ui/json-editor'
import { useModelStore } from '@/stores/modelStore'
import { useProjectStore } from '@/stores/projectStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'
import { truncateId } from '@/lib/utils'

export function DataExplorerPage() {
  const models = useModelStore((s) => s.models)
  const activeProject = useProjectStore((s) => s.activeProject)
  const navigate = useNavigate()
  const toast = useUIStore((s) => s.toast)

  const [collection, setCollection] = useState('')
  const [docs, setDocs] = useState<Record<string, unknown>[]>([])
  const [loading, setLoading] = useState(false)
  const [page, setPage] = useState(0)
  const [search, setSearch] = useState('')
  const [selectedDoc, setSelectedDoc] = useState<Record<string, unknown> | null>(null)
  const [newDocOpen, setNewDocOpen] = useState(false)
  const [newDocBody, setNewDocBody] = useState('{}')
  const limit = 20

  const model = models.find((m) => m.name === collection)

  const loadDocs = async (coll: string) => {
    if (!coll) return
    setLoading(true)
    try {
      let path = `/api/${coll}?limit=${limit}&skip=${page * limit}`
      if (search) path += `&filter=${encodeURIComponent(search)}`
      const data = await api.get<Record<string, unknown>[]>(path)
      setDocs(data)
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed to load', 'error')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (models.length) {
      if (!collection || !models.find((m) => m.name === collection)) {
        setCollection(models[0].name)
      }
    }
  }, [models])

  useEffect(() => {
    loadDocs(collection)
  }, [collection, page, activeProject])

  const handleCreate = async () => {
    try {
      const body = JSON.parse(newDocBody)
      await api.post(`/api/${collection}`, body)
      toast('Document created', 'success')
      setNewDocOpen(false)
      setNewDocBody('{}')
      loadDocs(collection)
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Create failed', 'error')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document?')) return
    try {
      await api.delete(`/api/${collection}/${id}`)
      toast('Deleted', 'info')
      loadDocs(collection)
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    }
  }

  const columns = model?.fields?.map((f) => f.name) || []

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => navigate('/')}>
            <ArrowLeft size={16} />
          </Button>
          <h1 className="text-2xl font-bold text-slate-100">Data Explorer</h1>
        </div>
        <div className="flex items-center gap-2">
          <Button size="sm" variant="secondary" onClick={() => loadDocs(collection)} loading={loading}>
            <RefreshCw size={14} />
          </Button>
          <Button size="sm" onClick={() => { setNewDocBody('{}'); setNewDocOpen(true) }}>
            <Plus size={14} /> Insert Document
          </Button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex items-center gap-4">
        <select
          value={collection}
          onChange={(e) => { setCollection(e.target.value); setPage(0) }}
          className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
        >
          {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
        </select>
        <Input
          placeholder="Filter: field__op=value"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
          onKeyDown={(e) => { if (e.key === 'Enter') loadDocs(collection) }}
        />
        <div className="flex items-center gap-1 text-sm text-slate-500">
          <Button size="sm" variant="ghost" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
            <ChevronLeft size={14} />
          </Button>
          <span className="px-2">Page {page + 1}</span>
          <Button size="sm" variant="ghost" disabled={docs.length < limit} onClick={() => setPage((p) => p + 1)}>
            <ChevronRight size={14} />
          </Button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-800 bg-slate-900/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">_id</th>
                {columns.slice(0, 6).map((col) => (
                  <th key={col} className="px-4 py-3 text-left text-xs font-semibold text-slate-500 uppercase">{col}</th>
                ))}
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {docs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-4 py-12 text-center text-sm text-slate-600">
                    {loading ? '⏳ Loading...' : 'No documents found'}
                  </td>
                </tr>
              ) : (
                docs.map((doc, i) => (
                  <motion.tr
                    key={(doc._id as string) || i}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    transition={{ delay: i * 0.02 }}
                    className="border-b border-slate-800/50 hover:bg-slate-800/30 transition-colors cursor-pointer"
                    onClick={() => setSelectedDoc(doc)}
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-400">
                      {truncateId((doc._id as string) || '')}
                    </td>
                    {columns.slice(0, 6).map((col) => {
                      const val = doc[col]
                      return (
                        <td key={col} className="px-4 py-3 text-sm text-slate-300 max-w-[200px] truncate">
                          {typeof val === 'object' ? JSON.stringify(val) : String(val ?? '—')}
                        </td>
                      )
                    })}
                    <td className="px-4 py-3 text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => { e.stopPropagation(); handleDelete(doc._id as string) }}
                      >
                        <Trash2 size={12} className="text-red-400" />
                      </Button>
                    </td>
                  </motion.tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* View document modal */}
      <Modal open={!!selectedDoc} onClose={() => setSelectedDoc(null)} title="Document" size="lg">
        {selectedDoc && (
          <pre className="text-xs text-slate-300 font-mono leading-relaxed overflow-x-auto max-h-96">
            {JSON.stringify(selectedDoc, null, 2)}
          </pre>
        )}
      </Modal>

      {/* New document modal */}
      <Modal open={newDocOpen} onClose={() => setNewDocOpen(false)} title="Insert Document" size="lg">
        <JSONEditor value={newDocBody} onChange={setNewDocBody} height="250px" />
        <div className="flex justify-end gap-2 mt-4">
          <Button variant="secondary" onClick={() => setNewDocOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate}>Create</Button>
        </div>
      </Modal>
    </div>
  )
}
