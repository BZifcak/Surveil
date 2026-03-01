import { useEffect, useRef, useState } from 'react'

export const BACKEND = 'http://localhost:8000'

export function formatEventType(type: string): string {
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}
const WS_URL = 'ws://localhost:8000/ws/events'
const THREAT_WINDOW_MS = 10_000
const THREAT_TYPES = new Set(['weapon_detected', 'fight_detected'])

export function isThreatEvent(eventType: string): boolean {
  return THREAT_TYPES.has(eventType)
}

export interface CameraInfo {
  id: string             // "cam_0"
  name: string
  location: string
  status: 'online' | 'offline'
  stream_url: string
}

export interface DetectionEvent {
  camera_id: string
  event_type: string
  timestamp: string
  confidence: number
  bounding_box: { x: number; y: number; width: number; height: number }
}

export interface CamState {
  latestByType: Record<string, DetectionEvent>
  hasThreat: boolean
  hasActivity: boolean
  lastEvent: DetectionEvent | null
}

const MAX_LOG_EVENTS = 500
const LOG_FLUSH_MS = 1000

export function useBackend() {
  const [cameras, setCameras] = useState<CameraInfo[]>([])
  const [camState, setCamState] = useState<Record<string, CamState>>({})
  const [eventLog, setEventLog] = useState<DetectionEvent[]>([])
  const [threatCount, setThreatCount] = useState(0)
  const wsRef = useRef<WebSocket | null>(null)
  const logBufferRef = useRef<DetectionEvent[]>([])

  // Fetch camera list once
  useEffect(() => {
    fetch(`${BACKEND}/cameras`)
      .then(r => r.json())
      .then(setCameras)
      .catch(() => {})
  }, [])

  // Flush buffered log events once per second
  useEffect(() => {
    const timer = setInterval(() => {
      const buf = logBufferRef.current
      if (buf.length === 0) return
      logBufferRef.current = []
      setEventLog(prev => {
        const merged = [...prev, ...buf]
        return merged.length > MAX_LOG_EVENTS
          ? merged.slice(merged.length - MAX_LOG_EVENTS)
          : merged
      })
    }, LOG_FLUSH_MS)
    return () => clearInterval(timer)
  }, [])

  // WebSocket with auto-reconnect
  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onmessage = e => {
        try {
          const ev: DetectionEvent = JSON.parse(e.data)
          logBufferRef.current.push(ev)
          if (isThreatEvent(ev.event_type)) {
            setThreatCount(c => c + 1)
          }
          setCamState(prev => {
            const existing = prev[ev.camera_id]
            const latestByType = {
              ...(existing?.latestByType ?? {}),
              [ev.event_type]: ev,
            }
            const evtList = Object.values(latestByType)
            const lastEvent = evtList.reduce<DetectionEvent | null>((a, b) =>
              !a || new Date(b.timestamp) > new Date(a.timestamp) ? b : a, null)
            return {
              ...prev,
              [ev.camera_id]: {
                latestByType,
                hasThreat: !!latestByType['weapon_detected'] || !!latestByType['fight_detected'],
                hasActivity: true,
                lastEvent,
              },
            }
          })
        } catch { /* ignore malformed messages */ }
      }

      ws.onclose = () => setTimeout(connect, 2000)
    }

    connect()
    return () => { wsRef.current?.close() }
  }, [])

  // Expire stale events every 2s
  useEffect(() => {
    const timer = setInterval(() => {
      const now = Date.now()
      setCamState(prev => {
        const next: Record<string, CamState> = {}
        for (const [id, state] of Object.entries(prev)) {
          const fresh = Object.fromEntries(
            Object.entries(state.latestByType).filter(
              ([, ev]) => now - new Date(ev.timestamp).getTime() < THREAT_WINDOW_MS
            )
          )
          if (!Object.keys(fresh).length) continue
          const evtList = Object.values(fresh)
          const lastEvent = evtList.reduce<DetectionEvent | null>((a, b) =>
            !a || new Date(b.timestamp) > new Date(a.timestamp) ? b : a, null)
          next[id] = {
            latestByType: fresh,
            hasThreat: !!fresh['weapon_detected'] || !!fresh['fight_detected'],
            hasActivity: true,
            lastEvent,
          }
        }
        return next
      })
    }, 2000)
    return () => clearInterval(timer)
  }, [])

  return { cameras, camState, eventLog, threatCount }
}
