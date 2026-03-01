import React, { useEffect, useMemo, useRef, useState } from 'react'
import './Cam.css'
import type { CamState, CameraInfo } from './useBackend'
import { BACKEND, formatEventType, isThreatEvent } from './useBackend'

interface CameraGridProps {
  cameraCount?: number
  selected?: number
  onSelect?: (id: number) => void
  edgeToEdge?: boolean
  camState?: Record<string, CamState>
  apiCameras?: CameraInfo[]
  page?: number
  onPageChange?: (page: number) => void
}

function Chevron({ direction }: { direction: 'left' | 'right' }) {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d={direction === 'left' ? 'M8 1.5L3 6L8 10.5' : 'M4 1.5L9 6L4 10.5'}
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="square"
        strokeLinejoin="miter"
      />
    </svg>
  )
}

// ── Single camera tile ──────────────────────────────────────────────────────

const POLL_INTERVAL = 66 // ms between snapshot fetches (~15 fps)

function CameraTile({
  id,
  selected = false,
  onClick,
  state,
  snapshotUrl,
}: {
  id: number
  selected?: boolean
  onClick?: () => void
  state?: CamState
  snapshotUrl: string
}) {
  const [src, setSrc] = useState<string | null>(null)
  const [offline, setOffline] = useState(false)
  const blobRef = useRef<string | null>(null)

  useEffect(() => {
    let active = true
    const poll = async () => {
      while (active) {
        try {
          const res = await fetch(snapshotUrl)
          if (!active) break
          if (!res.ok) { setOffline(true); break }
          const blob = await res.blob()
          if (!active) break
          const url = URL.createObjectURL(blob)
          if (blobRef.current) URL.revokeObjectURL(blobRef.current)
          blobRef.current = url
          setSrc(url)
          setOffline(false)
        } catch {
          if (active) setOffline(true)
          break
        }
        await new Promise(r => setTimeout(r, POLL_INTERVAL))
      }
    }
    poll()
    return () => {
      active = false
      if (blobRef.current) URL.revokeObjectURL(blobRef.current)
      blobRef.current = null
    }
  }, [snapshotUrl])

  const hasThreat = state?.hasThreat ?? false
  const threatCls = hasThreat ? 'cam-tile--threat' : ''

  return (
    <button
      type="button"
      className={`cam-tile ${selected ? 'cam-tile--selected' : ''} ${threatCls}`}
      onClick={onClick}
    >
      {offline || !src ? (
        <div className="cam-empty">
          <span className="cam-empty-icon">CAM {id + 1}</span>
          <span>No Signal</span>
        </div>
      ) : (
        <img
          src={src}
          alt={`Camera ${id}`}
          className="cam-image"
        />
      )}

      <div className="cam-label">CAM {id + 1}</div>
    </button>
  )
}

// ── Status panel for selected camera ────────────────────────────────────────

function StatusPanel({ camId, state }: { camId: number; state?: CamState }) {
  const events = useMemo(
    () => Object.values(state?.latestByType ?? {}),
    [state?.latestByType]
  )

  return (
    <div className="cam-status-panel">
      <span className="cam-status-label">CAM {camId + 1}</span>
      {events.length === 0 ? (
        <span className="cam-status-idle">No activity</span>
      ) : (
        events.map((evt, i) => (
          <span
            key={i}
            className={`cam-status-event ${isThreatEvent(evt.event_type) ? 'cam-status-event--threat' : evt.event_type === 'motion' ? 'cam-status-event--motion' : ''}`}
          >
            {evt.event_type === 'person_detected' ? 'Person(s) detected' : evt.event_type === 'motion' ? 'Motion Detected' : formatEventType(evt.event_type)}
          </span>
        ))
      )}
    </div>
  )
}

// ── Camera grid ─────────────────────────────────────────────────────────────

const CameraGrid: React.FC<CameraGridProps> = ({
  cameraCount = 12,
  selected,
  onSelect,
  edgeToEdge = false,
  camState,
  page,
  onPageChange,
}) => {
  const snapshotUrlFor = (id: number): string => {
    return `${BACKEND}/snapshot/cam_${id}`
  }

  // Build cameras sorted: threats first, then by id
  const cameras = useMemo(() => {
    const base = Array.from({ length: cameraCount }, (_, i) => ({ id: i }))
    return base.sort((a, b) => {
      const stA = camState?.[`cam_${a.id}`]
      const stB = camState?.[`cam_${b.id}`]
      if (stA?.hasThreat && !stB?.hasThreat) return -1
      if (!stA?.hasThreat && stB?.hasThreat) return 1
      return a.id - b.id
    })
  }, [cameraCount, camState])

  const [internalSelected, setInternalSelected] = useState<number>(0)
  const [internalPage, setInternalPage] = useState(0)

  const selectedId = selected ?? internalSelected
  const activeId = cameras.some((cam) => cam.id === selectedId) ? selectedId : cameras[0]?.id
  const featured = cameras.find((cam) => cam.id === activeId) ?? cameras[0]

  const handleSelect = (id: number) => {
    setInternalSelected(id)
    onSelect?.(id)
  }

  if (!featured) return null

  // ── Split mode: featured + status + paginated preview grid ──────────────
  if (edgeToEdge) {
    const others = cameras.filter(c => c.id !== activeId)
    const previewPageSize = 6
    const previewPageCount = Math.max(1, Math.ceil(others.length / previewPageSize))
    const previewPage = Math.min(page ?? internalPage, previewPageCount - 1)
    const previewStart = previewPage * previewPageSize
    const previewCameras = others.slice(previewStart, previewStart + previewPageSize)

    const setPreviewPage = (p: number) => {
      setInternalPage(p)
      onPageChange?.(p)
    }

    return (
      <div className="cam-layout cam-layout--edge">
        {/* Featured camera */}
        <div className="cam-featured">
          <CameraTile
            id={featured.id}
            selected
            onClick={() => handleSelect(featured.id)}
            state={camState?.[`cam_${featured.id}`]}
            snapshotUrl={snapshotUrlFor(featured.id)}
          />
        </div>

        {/* Status text */}
        <StatusPanel camId={featured.id} state={camState?.[`cam_${featured.id}`]} />

        {/* Preview grid */}
        <div className="cam-preview-section">
          <div
            className="cam-grid cam-grid--preview"
            style={{ gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}
          >
            {previewCameras.map((cam) => (
              <CameraTile
                key={cam.id}
                id={cam.id}
                selected={cam.id === activeId}
                onClick={() => handleSelect(cam.id)}
                state={camState?.[`cam_${cam.id}`]}
                snapshotUrl={snapshotUrlFor(cam.id)}
              />
            ))}
          </div>
          {previewPageCount > 1 && (
            <div className="cam-page-nav">
              <button
                className="cam-page-btn"
                onClick={() => setPreviewPage((previewPage - 1 + previewPageCount) % previewPageCount)}
              >
                <Chevron direction="left" />
              </button>
              <span className="cam-page-indicator">{previewPage + 1} / {previewPageCount}</span>
              <button
                className="cam-page-btn"
                onClick={() => setPreviewPage((previewPage + 1) % previewPageCount)}
              >
                <Chevron direction="right" />
              </button>
            </div>
          )}
        </div>
      </div>
    )
  }

  // ── Camera mode: 2×3 paginated grid ─────────────────────────────────────
  const gridPageSize = 6
  const gridPageCount = Math.max(1, Math.ceil(cameras.length / gridPageSize))
  const gridPage = Math.min(page ?? internalPage, gridPageCount - 1)
  const gridStart = gridPage * gridPageSize
  const gridCameras = cameras.slice(gridStart, gridStart + gridPageSize)

  const setGridPage = (p: number) => {
    setInternalPage(p)
    onPageChange?.(p)
  }

  return (
    <div className="cam-layout">
      <div
        className="cam-grid cam-grid--full"
        style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gridTemplateRows: 'repeat(3, minmax(0, 1fr))' }}
      >
        {gridCameras.map((cam) => (
          <CameraTile
            key={cam.id}
            id={cam.id}
            selected={cam.id === activeId}
            onClick={() => handleSelect(cam.id)}
            state={camState?.[`cam_${cam.id}`]}
            snapshotUrl={snapshotUrlFor(cam.id)}
          />
        ))}
      </div>
      {gridPageCount > 1 && (
        <div className="cam-page-nav">
          <button
            className="cam-page-btn"
            onClick={() => setGridPage((gridPage - 1 + gridPageCount) % gridPageCount)}
          >
            <Chevron direction="left" />
          </button>
          <span className="cam-page-indicator">{gridPage + 1} / {gridPageCount}</span>
          <button
            className="cam-page-btn"
            onClick={() => setGridPage((gridPage + 1) % gridPageCount)}
          >
            <Chevron direction="right" />
          </button>
        </div>
      )}
    </div>
  )
}

export default CameraGrid
