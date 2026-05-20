import { useEffect, useState } from 'react'
import { Key, Plus, Trash2, Copy, Eye, EyeOff } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select } from '@/components/ui/select'
import { Modal } from '@/components/ui/modal'
import { api } from '@/services/api'
import { useUIStore } from '@/stores/uiStore'
import type { ApiKey } from '@/types'

export function ApiKeysPage() {
  const [keys, setKeys] = useState<ApiKey[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [role, setRole] = useState('viewer')
  const [newKey, setNewKey] = useState<string | null>(null)
  const [showKey, setShowKey] = useState<string | null>(null)
  const toast = useUIStore((s) => s.toast)

  useEffect(() => { loadKeys() }, []) // eslint-disable-line

  const loadKeys = async () => {
    try {
      const data = await api.get<ApiKey[]>('/api/keys/')
      setKeys(data)
    } catch { setKeys([]) }
  }

  const handleCreate = async () => {
    try {
      const r = await api.post<{ key: string; id: string; message: string }>(`/api/keys/?name=${encodeURIComponent(name)}&role=${encodeURIComponent(role)}`)
      setNewKey(r.key)
      toast('API key created — copy it now, it won\'t be shown again', 'success')
      loadKeys()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast('Copied to clipboard', 'info')
  }

  const handleDelete = async (keyId: string) => {
    try {
      await api.delete(`/api/keys/${keyId}`)
      toast('Key deleted', 'success')
      loadKeys()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Failed', 'error')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-100">API Keys</h1>
        <Button size="sm" onClick={() => { setNewKey(null); setShowCreate(true) }}><Plus size={14} className="mr-1" /> New Key</Button>
      </div>

      <div className="space-y-3">
        {keys.map((k) => (
          <div key={k.id} className="bg-slate-800/30 border border-slate-700/50 rounded-xl p-4 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Key size={16} className="text-amber-400" />
              <div>
                <p className="text-sm text-slate-200 font-medium">{k.name}</p>
                <div className="flex items-center gap-2 text-xs text-slate-500">
                  <span>{k.role}</span>
                  <span>·</span>
                  <span>{k.key_preview}</span>
                  {showKey === k.id && (
                    <>
                      <span>·</span>
                      <button onClick={() => setShowKey(null)}><EyeOff size={12} /></button>
                    </>
                  )}
                  {showKey !== k.id && (
                    <button onClick={() => setShowKey(k.id)}><Eye size={12} /></button>
                  )}
                </div>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button onClick={() => copyToClipboard(k.key_preview)} className="text-slate-500 hover:text-slate-300"><Copy size={14} /></button>
              <button onClick={() => handleDelete(k.id)} className="text-slate-500 hover:text-red-400"><Trash2 size={14} /></button>
            </div>
          </div>
        ))}
        {keys.length === 0 && <p className="text-sm text-slate-500 text-center py-8">No API keys. Create one to get started.</p>}
      </div>

      {newKey ? (
        <Modal open={true} onClose={() => { setNewKey(null); setShowCreate(false) }} title="API Key Created">
          <p className="text-sm text-amber-400 mb-3">Copy this key now. It will not be shown again.</p>
          <div className="bg-slate-900 border border-slate-700 rounded-lg p-3 font-mono text-xs text-slate-200 break-all mb-4">{newKey}</div>
          <div className="flex gap-2">
            <Button className="flex-1" onClick={() => { copyToClipboard(newKey); setNewKey(null); setShowCreate(false) }}><Copy size={14} className="mr-1" /> Copy & Close</Button>
            <Button variant="ghost" onClick={() => { setNewKey(null); setShowCreate(false) }}>Close</Button>
          </div>
        </Modal>
      ) : (
        <Modal open={showCreate} onClose={() => setShowCreate(false)} title="Create API Key">
          <div className="space-y-4">
            <Input label="Key Name" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. development" />
            <Select label="Role" value={role} onChange={(e) => setRole(e.target.value)} options={[
              { value: 'admin', label: 'Admin' },
              { value: 'editor', label: 'Editor' },
              { value: 'viewer', label: 'Viewer' },
            ]} />
            <Button className="w-full" onClick={handleCreate}>Generate Key</Button>
          </div>
        </Modal>
      )}
    </div>
  )
}
