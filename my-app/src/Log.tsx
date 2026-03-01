import { useMemo, useState } from 'react'
import type { DetectionEvent } from './useBackend'
import './Log.css'

interface LogProps {
  events: DetectionEvent[]
}

type SortField = 'timestamp' | 'camera_id' | 'event_type' | 'confidence'
type SortDir = 'asc' | 'desc'

export default function Log({ events }: LogProps) {
  const [sortField, setSortField] = useState<SortField>('timestamp')
  const [sortDir, setSortDir] = useState<SortDir>('desc')
  const [filterCamera, setFilterCamera] = useState<string>('')
  const [filterType, setFilterType] = useState<string>('')

  const cameraIds = useMemo(() => {
    const ids = new Set(events.map(e => e.camera_id))
    return Array.from(ids).sort()
  }, [events])

  const eventTypes = useMemo(() => {
    const types = new Set(events.map(e => e.event_type))
    return Array.from(types).sort()
  }, [events])

  const sorted = useMemo(() => {
    let filtered = events
    if (filterCamera) filtered = filtered.filter(e => e.camera_id === filterCamera)
    if (filterType) filtered = filtered.filter(e => e.event_type === filterType)

    return [...filtered].sort((a, b) => {
      let cmp = 0
      switch (sortField) {
        case 'timestamp':
          cmp = new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
          break
        case 'camera_id':
          cmp = a.camera_id.localeCompare(b.camera_id)
          break
        case 'event_type':
          cmp = a.event_type.localeCompare(b.event_type)
          break
        case 'confidence':
          cmp = a.confidence - b.confidence
          break
      }
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [events, sortField, sortDir, filterCamera, filterType])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc')
    } else {
      setSortField(field)
      setSortDir('desc')
    }
  }

  const arrow = (field: SortField) =>
    sortField === field ? (sortDir === 'asc' ? ' \u25B2' : ' \u25BC') : ''

  const camLabel = (camId: string) => {
    const n = parseInt(camId.replace('cam_', ''), 10)
    return `CAM ${n + 1}`
  }

  return (
    <div className="log-container">
      <div className="log-toolbar">
        <span className="log-count">{sorted.length} events</span>
        <select
          className="log-filter"
          value={filterCamera}
          onChange={e => setFilterCamera(e.target.value)}
        >
          <option value="">All Cameras</option>
          {cameraIds.map(id => (
            <option key={id} value={id}>{camLabel(id)}</option>
          ))}
        </select>
        <select
          className="log-filter"
          value={filterType}
          onChange={e => setFilterType(e.target.value)}
        >
          <option value="">All Types</option>
          {eventTypes.map(t => (
            <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>
          ))}
        </select>
      </div>

      <div className="log-table-wrap">
        <table className="log-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('timestamp')}>Time{arrow('timestamp')}</th>
              <th onClick={() => handleSort('camera_id')}>Camera{arrow('camera_id')}</th>
              <th onClick={() => handleSort('event_type')}>Event{arrow('event_type')}</th>
              <th onClick={() => handleSort('confidence')}>Confidence{arrow('confidence')}</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((ev, i) => (
              <tr key={i} className={ev.event_type === 'weapon_detected' ? 'log-row--threat' : ''}>
                <td>{new Date(ev.timestamp).toLocaleTimeString()}</td>
                <td>{camLabel(ev.camera_id)}</td>
                <td>{ev.event_type.replace(/_/g, ' ')}</td>
                <td>{Math.round(ev.confidence * 100)}%</td>
              </tr>
            ))}
            {sorted.length === 0 && (
              <tr><td colSpan={4} className="log-empty">No events recorded yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
