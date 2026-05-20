import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Trash2, UserPlus } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Modal } from '@/components/ui/modal'
import { api } from '@/services/api'
import { useUIStore } from '@/stores/uiStore'
import type { User } from '@/types'

export function UsersPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(false)
  const [showCreate, setShowCreate] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('user')
  const toast = useUIStore((s) => s.toast)

  useEffect(() => { loadUsers() }, []) // eslint-disable-line

  const loadUsers = async () => {
    setLoading(true)
    try {
      const data = await api.get<User[]>('/api/auth/users')
      setUsers(data)
    } catch { setUsers([]) }
    finally { setLoading(false) }
  }

  const handleCreate = async () => {
    try {
      await api.post('/api/auth/users', { email, password, role })
      toast('User created', 'success')
      setShowCreate(false); setEmail(''); setPassword('')
      loadUsers()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleDelete = async (userId: string) => {
    try {
      await api.delete(`/api/auth/users/${userId}`)
      toast('User deleted', 'success')
      loadUsers()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await api.patch(`/api/auth/users/${userId}/role`, { role: newRole })
      toast('Role updated', 'success')
      loadUsers()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-100">Users</h1>
        <Button size="sm" onClick={() => setShowCreate(true)}><UserPlus size={14} className="mr-1" /> Add User</Button>
      </div>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700/50 text-slate-500 text-xs uppercase">
              <th className="text-left p-3 font-medium">Email</th>
              <th className="text-left p-3 font-medium">Role</th>
              <th className="text-left p-3 font-medium">Verified</th>
              <th className="text-left p-3 font-medium">Active</th>
              <th className="text-right p-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                <td className="p-3 text-slate-200">{u.email}</td>
                <td className="p-3">
                  <select
                    value={u.role}
                    onChange={(e) => handleRoleChange(u.id, e.target.value)}
                    className="bg-slate-700/50 text-slate-300 text-xs rounded px-2 py-1 border border-slate-600"
                  >
                    <option value="admin">admin</option>
                    <option value="editor">editor</option>
                    <option value="viewer">viewer</option>
                    <option value="user">user</option>
                  </select>
                </td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${u.email_verified ? 'bg-emerald-500/20 text-emerald-400' : 'bg-slate-600/20 text-slate-500'}`}>
                    {u.email_verified ? 'Yes' : 'No'}
                  </span>
                </td>
                <td className="p-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${u.is_active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-red-500/20 text-red-400'}`}>
                    {u.is_active ? 'Active' : 'Disabled'}
                  </span>
                </td>
                <td className="p-3 text-right">
                  <button onClick={() => handleDelete(u.id)} className="text-slate-500 hover:text-red-400 transition-colors">
                    <Trash2 size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create User">
        <div className="space-y-4">
          <Input label="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input label="Password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Select label="Role" value={role} onChange={(e) => setRole(e.target.value)} options={[
            { value: 'admin', label: 'Admin' },
            { value: 'editor', label: 'Editor' },
            { value: 'viewer', label: 'Viewer' },
            { value: 'user', label: 'User' },
          ]} />
          <Button className="w-full" onClick={handleCreate}>Create User</Button>
        </div>
      </Modal>
    </div>
  )
}
