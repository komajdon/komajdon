import { useEffect, useState } from 'react'
import { socket } from '@/services/socket'
import { api } from '@/services/api'

export function useRealtime(collection: string | null) {
  const [connected, setConnected] = useState(false)
  const [events, setEvents] = useState<{ event: string; data: unknown; ts: number }[]>([])

  useEffect(() => {
    if (!collection) return

    const token = api.getToken()
    if (!token) return

    const unsub1 = socket.on('_connected', () => setConnected(true))
    const unsub2 = socket.on('_disconnected', () => setConnected(false))
    const unsub3 = socket.on('create', (data: unknown) => {
      setEvents((prev) => [...prev.slice(-49), { event: 'create', data, ts: Date.now() }])
    })
    const unsub4 = socket.on('update', (data: unknown) => {
      setEvents((prev) => [...prev.slice(-49), { event: 'update', data, ts: Date.now() }])
    })
    const unsub5 = socket.on('delete', (data: unknown) => {
      setEvents((prev) => [...prev.slice(-49), { event: 'delete', data, ts: Date.now() }])
    })

    socket.connect(collection, token)

    return () => {
      unsub1()
      unsub2()
      unsub3()
      unsub4()
      unsub5()
      if (!document.querySelector('[data-keep-socket]')) {
        socket.disconnect()
      }
    }
  }, [collection])

  return { connected, events, clear: () => setEvents([]) }
}
