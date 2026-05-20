import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FolderKanban, Plus, Trash2, Check, Edit3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { useProjectStore } from '@/stores/projectStore'
import { useUIStore } from '@/stores/uiStore'
import { api } from '@/services/api'

export function ProjectsPage() {
  const projects = useProjectStore((s) => s.projects)
  const activeProject = useProjectStore((s) => s.activeProject)
  const loadProjects = useProjectStore((s) => s.loadProjects)
  const createProject = useProjectStore((s) => s.createProject)
  const selectProject = useProjectStore((s) => s.selectProject)
  const toast = useUIStore((s) => s.toast)

  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [slug, setSlug] = useState('')
  const [desc, setDesc] = useState('')
  const [loading, setLoading] = useState(false)

  const [showEdit, setShowEdit] = useState(false)
  const [editId, setEditId] = useState('')
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')

  useEffect(() => { loadProjects() }, [loadProjects])

  const handleCreate = async () => {
    if (!name || !slug) { toast('Name and slug required', 'error'); return }
    setLoading(true)
    try {
      await createProject(name, slug, desc)
      toast('Project created', 'success')
      setShowCreate(false); setName(''); setSlug(''); setDesc('')
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    } finally { setLoading(false) }
  }

  const handleEdit = async () => {
    if (!editId) return
    try {
      await api.put(`/api/projects/${editId}`, { name: editName, description: editDesc })
      toast('Project updated', 'success')
      setShowEdit(false)
      loadProjects()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Update failed', 'error')
    }
  }

  const handleDelete = async (projectId: string) => {
    if (!confirm('Delete this project? All isolated data will be lost.')) return
    try {
      await api.delete(`/api/projects/${projectId}`)
      toast('Project deleted', 'success')
      if (activeProject?.id === projectId) selectProject(null)
      loadProjects()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-100">Projects</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}><Plus size={14} className="mr-1" /> New Project</Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <motion.div
          onClick={() => selectProject(null)}
          className={`p-4 rounded-xl border cursor-pointer transition-all ${!activeProject ? 'bg-mongodb-green/5 border-mongodb-green/40' : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'}`}
        >
          <div className="flex items-center justify-between mb-2">
            <FolderKanban size={20} className="text-slate-400" />
            {!activeProject && <Check size={16} className="text-mongodb-green" />}
          </div>
          <h3 className="font-medium text-slate-200 text-sm">Global</h3>
          <p className="text-xs text-slate-500 mt-1">No project isolation — all data visible</p>
        </motion.div>

        {projects.map((p) => (
          <div key={p.id} className={`p-4 rounded-xl border transition-all relative group ${activeProject?.id === p.id ? 'bg-mongodb-green/5 border-mongodb-green/40' : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'}`}>
            <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={(e) => { e.stopPropagation(); setEditId(p.id); setEditName(p.name); setEditDesc(p.description); setShowEdit(true) }} className="text-slate-500 hover:text-slate-300 p-1"><Edit3 size={14} /></button>
              <button onClick={(e) => { e.stopPropagation(); handleDelete(p.id) }} className="text-slate-500 hover:text-red-400 p-1"><Trash2 size={14} /></button>
            </div>
            <div onClick={() => selectProject(p)} className="cursor-pointer">
              <div className="flex items-center justify-between mb-2">
                <FolderKanban size={20} className="text-emerald-400" />
                {activeProject?.id === p.id && <Check size={16} className="text-mongodb-green" />}
              </div>
              <h3 className="font-medium text-slate-200 text-sm">{p.name}</h3>
              <p className="text-xs text-slate-500 mt-1">{p.description || p.slug}</p>
            </div>
          </div>
        ))}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Project">
        <div className="space-y-4">
          <Input label="Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="My Shop" />
          <Input label="Slug" value={slug} onChange={(e) => setSlug(e.target.value)} placeholder="my-shop" />
          <Input label="Description (optional)" value={desc} onChange={(e) => setDesc(e.target.value)} />
          <Button className="w-full" loading={loading} onClick={handleCreate}>Create</Button>
        </div>
      </Modal>

      <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Project">
        <div className="space-y-4">
          <Input label="Name" value={editName} onChange={(e) => setEditName(e.target.value)} />
          <Input label="Description" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
          <Button className="w-full" onClick={handleEdit}>Save Changes</Button>
        </div>
      </Modal>
    </div>
  )
}
