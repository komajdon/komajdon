import { useEffect, useState } from 'react'
import { Shield, Plus, Trash2, Edit3 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Modal } from '@/components/ui/modal'
import { api } from '@/services/api'
import { useUIStore } from '@/stores/uiStore'
import type { Role, PermissionInfo } from '@/types'

export function RolesPage() {
  const [roles, setRoles] = useState<Role[]>([])
  const [permissions, setPermissions] = useState<PermissionInfo[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [selectedPerms, setSelectedPerms] = useState<string[]>([])
  const toast = useUIStore((s) => s.toast)

  const [showEdit, setShowEdit] = useState(false)
  const [editId, setEditId] = useState('')
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editPerms, setEditPerms] = useState<string[]>([])

  useEffect(() => { loadData() }, []) // eslint-disable-line

  const loadData = async () => {
    try {
      const [r, p] = await Promise.all([
        api.get<Role[]>('/api/roles/'),
        api.get<PermissionInfo[]>('/api/roles/permissions'),
      ])
      setRoles(r); setPermissions(p)
    } catch { /* ignore */ }
  }

  const togglePerm = (key: string) => {
    setSelectedPerms((prev) => prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key])
  }

  const toggleEditPerm = (key: string) => {
    setEditPerms((prev) => prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key])
  }

  const handleCreate = async () => {
    try {
      await api.post('/api/roles/', { name, description: desc, permissions: selectedPerms })
      toast('Role created', 'success')
      setShowCreate(false); setName(''); setDesc(''); setSelectedPerms([])
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleEdit = async () => {
    try {
      await api.put(`/api/roles/${editId}`, { name: editName, description: editDesc, permissions: editPerms })
      toast('Role updated', 'success')
      setShowEdit(false)
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleDelete = async (roleId: string) => {
    try {
      await api.delete(`/api/roles/${roleId}`)
      toast('Role deleted', 'success')
      loadData()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-100">Roles & Permissions</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}><Plus size={14} className="mr-1" /> New Role</Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {roles.map((role) => (
          <div key={role.id} className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <Shield size={16} className="text-emerald-400" />
                  <h3 className="font-medium text-slate-200">{role.name}</h3>
                  {role.is_default && <span className="text-[10px] text-slate-500 bg-slate-700/50 px-1.5 py-0.5 rounded">default</span>}
                </div>
                <div className="flex gap-1">
                  {!role.is_default && (
                    <>
                      <button onClick={() => { setEditId(role.id); setEditName(role.name); setEditDesc(role.description); setEditPerms(role.permissions); setShowEdit(true) }} className="text-slate-500 hover:text-slate-300"><Edit3 size={14} /></button>
                      <button onClick={() => handleDelete(role.id)} className="text-slate-500 hover:text-red-400"><Trash2 size={14} /></button>
                    </>
                  )}
                </div>
              </div>
            {role.description && <p className="text-xs text-slate-500 mb-3">{role.description}</p>}
            <div className="flex flex-wrap gap-1">
              {role.permissions.map((p) => (
                <span key={p} className="text-[10px] px-2 py-0.5 rounded-full bg-slate-700/50 text-slate-400">{p}</span>
              ))}
            </div>
          </div>
        ))}
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create Role">
        <div className="space-y-4">
          <Input label="Role Name" value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="Description" value={desc} onChange={(e) => setDesc(e.target.value)} />
          <div>
            <p className="text-sm font-medium text-slate-400 mb-2">Permissions</p>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {permissions.map((p) => (
                <label key={p.key} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:bg-slate-700/30 px-2 py-1 rounded">
                  <input type="checkbox" checked={selectedPerms.includes(p.key)} onChange={() => togglePerm(p.key)} className="rounded border-slate-600" />
                  <span className="font-mono text-[10px]">{p.key}</span>
                  <span className="text-slate-500">— {p.description}</span>
                </label>
              ))}
            </div>
          </div>
          <Button className="w-full" onClick={handleCreate}>Create Role</Button>
        </div>
      </Modal>

      <Modal open={showEdit} onClose={() => setShowEdit(false)} title="Edit Role">
        <div className="space-y-4">
          <Input label="Role Name" value={editName} onChange={(e) => setEditName(e.target.value)} />
          <Input label="Description" value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
          <div>
            <p className="text-sm font-medium text-slate-400 mb-2">Permissions</p>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {permissions.map((p) => (
                <label key={p.key} className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer hover:bg-slate-700/30 px-2 py-1 rounded">
                  <input type="checkbox" checked={editPerms.includes(p.key)} onChange={() => toggleEditPerm(p.key)} className="rounded border-slate-600" />
                  <span className="font-mono text-[10px]">{p.key}</span>
                  <span className="text-slate-500">— {p.description}</span>
                </label>
              ))}
            </div>
          </div>
          <Button className="w-full" onClick={handleEdit}>Save Changes</Button>
        </div>
      </Modal>
    </div>
  )
}
