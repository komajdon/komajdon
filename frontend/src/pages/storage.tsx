import { useEffect, useState, useRef } from 'react'
import { motion } from 'framer-motion'
import { HardDrive, Upload, Trash2, Download, File } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/services/api'
import { useModelStore } from '@/stores/modelStore'
import { useUIStore } from '@/stores/uiStore'
import type { UploadedFile } from '@/types'

export function StoragePage() {
  const models = useModelStore((s) => s.models)
  const toast = useUIStore((s) => s.toast)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [collection, setCollection] = useState('')
  const [files, setFiles] = useState<UploadedFile[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (models.length && !collection) setCollection(models[0].name)
  }, [models])

  useEffect(() => {
    if (collection) loadFiles()
  }, [collection])

  const loadFiles = async () => {
    if (!collection) return
    setLoading(true)
    try {
      const data = await api.get<{ files: UploadedFile[] }>(`/api/storage/list/${collection}`)
      setFiles(data.files || [])
    } catch {
      setFiles([])
    } finally { setLoading(false) }
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !collection) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const r = await api.upload<{ file_id: string; filename: string }>(`/api/storage/upload/${collection}`, formData)
      toast(`Uploaded ${r.filename}`, 'success')
      loadFiles()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Upload failed', 'error')
    } finally {
      setUploading(false)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const res = await fetch(`/api/storage/download/${fileId}`, {
        headers: api.getToken() ? { Authorization: `Bearer ${api.getToken()}` } : {},
      })
      if (!res.ok) throw new Error('Download failed')
      const blob = await res.blob()
      const a = document.createElement('a')
      a.href = URL.createObjectURL(blob)
      a.download = filename
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Download failed', 'error')
    }
  }

  const handleDelete = async (fileId: string) => {
    if (!confirm('Delete this file?')) return
    try {
      await api.delete(`/api/storage/delete/${fileId}`)
      toast('File deleted', 'success')
      loadFiles()
    } catch (e: unknown) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    }
  }

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-xl font-bold text-slate-100">File Storage</h1>
        <div className="flex items-center gap-3">
          <select
            value={collection}
            onChange={(e) => setCollection(e.target.value)}
            className="bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200"
          >
            {models.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
          </select>
          <input
            ref={fileInputRef}
            type="file"
            onChange={handleUpload}
            className="hidden"
          />
          <Button size="sm" loading={uploading} onClick={() => fileInputRef.current?.click()}>
            <Upload size={14} className="mr-1" /> Upload
          </Button>
        </div>
      </div>

      <div className="bg-slate-800/30 border border-slate-700/50 rounded-xl overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-sm text-slate-500">Loading...</div>
        ) : files.length === 0 ? (
          <div className="p-8 text-center text-sm text-slate-500">No files uploaded for this collection</div>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700/50 text-slate-500 text-xs uppercase">
                <th className="text-left p-3 font-medium">Filename</th>
                <th className="text-left p-3 font-medium">Type</th>
                <th className="text-left p-3 font-medium">Size</th>
                <th className="text-left p-3 font-medium">Uploaded</th>
                <th className="text-right p-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {files.map((f) => (
                <tr key={f.file_id} className="border-b border-slate-800/50 hover:bg-slate-800/20">
                  <td className="p-3 text-slate-200 flex items-center gap-2">
                    <File size={14} className="text-slate-500" />
                    {f.filename}
                  </td>
                  <td className="p-3 text-slate-400">{f.content_type}</td>
                  <td className="p-3 text-slate-400">{(f.size / 1024).toFixed(1)} KB</td>
                  <td className="p-3 text-slate-400">{f.upload_date ? new Date(f.upload_date).toLocaleDateString() : '—'}</td>
                  <td className="p-3 text-right">
                    <div className="flex gap-1 justify-end">
                      <button onClick={() => handleDownload(f.file_id, f.filename)} className="text-slate-500 hover:text-slate-300 p-1"><Download size={14} /></button>
                      <button onClick={() => handleDelete(f.file_id)} className="text-slate-500 hover:text-red-400 p-1"><Trash2 size={14} /></button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}