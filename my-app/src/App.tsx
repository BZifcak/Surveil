import { useEffect, useState } from 'react'
import './App.css'
import { LoadMap } from './Map'
import CameraGrid from './Cams'

type Mode =  'cam' | 'split'

const imageModules = import.meta.glob<{ default: string }>('./images/*.{jpg,jpeg,png,webp,gif}', { eager: true })
const images = Object.values(imageModules).map((mod) => mod.default)

function App() {
  const cameraCount = 12
  const panelPageSize = 4
  const [mode, setMode] = useState<Mode>('split')
  const [selected, setSelected] = useState<number>(1)
  const [cameraSelectorOpen, setCameraSelectorOpen] = useState<boolean>(false)
  const [cameraPanelPage, setCameraPanelPage] = useState<number>(0)
  const [showCameraHint, setShowCameraHint] = useState<boolean>(false)

  const setModeAndCloseSelector = (nextMode: Mode) => {
    setMode(nextMode)
    if (nextMode !== 'cam') {
      setCameraSelectorOpen(false)
    }
  }

  const shiftCamera = (delta: number) => {
    setSelected((current) => {
      const normalized = ((current - 1 + delta) % cameraCount + cameraCount) % cameraCount
      return normalized + 1
    })
  }

  const shiftCameraPage = (delta: number) => {
    const pageCount = Math.max(1, Math.ceil(cameraCount / panelPageSize))
    setCameraPanelPage((current) => {
      const normalized = ((current + delta) % pageCount + pageCount) % pageCount
      return normalized
    })
  }

  const handleArrow = (delta: number) => {
    if (mode === 'cam' && cameraSelectorOpen) {
      shiftCameraPage(delta)
      return
    }
    shiftCamera(delta)
  }

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null
      if (
        target &&
        (target.tagName === 'INPUT' ||
          target.tagName === 'TEXTAREA' ||
          target.isContentEditable)
      ) {
        return
      }

      if (event.key.toLowerCase() === 'c' && mode === 'cam') {
        event.preventDefault()
        setCameraSelectorOpen((open) => {
          const next = !open
          if (next) {
            setCameraPanelPage(0)
          }
          return next
        })
        return
      }

      if (event.key.toLowerCase() === 'a') {
        event.preventDefault()
        setModeAndCloseSelector('split')
        return
      }

      if (event.key.toLowerCase() === 'd') {
        event.preventDefault()
        setModeAndCloseSelector('cam')
        return
      }

      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault()
        if (mode === 'cam' && cameraSelectorOpen) {
          shiftCameraPage(-1)
        } else {
          shiftCamera(-1)
        }
      } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault()
        if (mode === 'cam' && cameraSelectorOpen) {
          shiftCameraPage(1)
        } else {
          shiftCamera(1)
        }
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [cameraSelectorOpen, mode, panelPageSize, selected])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100vh', margin: 0, minWidth: 0 }}>
      {/* Navbar */}
      <nav style={{
        position: 'relative',
        display: 'flex',
        justifyContent: 'center',
        gap: '8px',
        padding: '10px 20px',
        backgroundColor: '#1a1a1a',
        borderBottom: '1px solid #333'
      }}>
        <button onClick={() => setModeAndCloseSelector('split')} style={btnStyle(mode === 'split')}>Split</button>
        <button onClick={() => setModeAndCloseSelector('cam')} style={btnStyle(mode === 'cam')}>Camera</button>
        {mode === 'cam' && (
          <span
            style={{ position: 'relative', display: 'inline-flex', alignItems: 'center' }}
            onMouseEnter={() => setShowCameraHint(true)}
            onMouseLeave={() => setShowCameraHint(false)}
          >
            <span
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '22px',
                height: '22px',
                borderRadius: '50%',
                border: '1px solid #3a485a',
                color: '#b9d8ff',
                fontSize: '12px',
                fontWeight: 700,
                cursor: 'help',
                userSelect: 'none',
              }}
              aria-label="Press C to pull up the camera menu"
            >
              i
            </span>
            {showCameraHint && (
              <span
                style={{
                  position: 'absolute',
                  top: '30px',
                  left: '50%',
                  transform: 'translateX(-50%)',
                  whiteSpace: 'nowrap',
                  padding: '6px 10px',
                  borderRadius: '6px',
                  border: '1px solid #3a485a',
                  background: '#101823',
                  color: '#d9ecff',
                  fontSize: '12px',
                  zIndex: 20,
                  boxShadow: '0 8px 16px rgba(0, 0, 0, 0.35)',
                }}
              >
                Press C to pull up the camera menu
              </span>
            )}
          </span>
        )}
      </nav>

      {/* Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minWidth: 0 }}>
        {(mode === 'split') && (
          <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
            <LoadMap selected={selected} onSelect={setSelected} />
          </div>
        )}

        {mode === 'split' && (
          <div style={{ width: '1px', backgroundColor: '#444' }} />
        )}

        {(mode === 'cam' || mode === 'split') && (
          <div style={{ flex: 1, overflow: 'hidden', minWidth: 0, display: 'flex', flexDirection: 'column', position: 'relative' }}>
            {mode === 'cam' && (
              <>
                <button
                  onClick={() => handleArrow(-1)}
                  style={arrowBtnStyle('left')}
                  aria-label="Previous camera"
                >
                  ←
                </button>
                <button
                  onClick={() => handleArrow(1)}
                  style={arrowBtnStyle('right')}
                  aria-label="Next camera"
                >
                  →
                </button>
              </>
            )}
            <div style={{ flex: 1, minHeight: 0 }}>
            <CameraGrid
              cameraCount={cameraCount}
              columns={6}
              images={images}
              selected={selected}
              onSelect={setSelected}
              selectorOpen={cameraSelectorOpen}
              onSelectorOpenChange={setCameraSelectorOpen}
              edgeToEdge={mode === 'split'}
              panelPageIndex={mode === 'cam' ? cameraPanelPage : undefined}
              onPanelPageChange={mode === 'cam' ? setCameraPanelPage : undefined}
            />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function btnStyle(active: boolean): React.CSSProperties {
  return {
    padding: '8px 20px',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    backgroundColor: active ? '#555' : '#2a2a2a',
    color: active ? '#fff' : '#aaa',
    fontWeight: active ? 'bold' : 'normal',
  }
}

function arrowBtnStyle(side: 'left' | 'right'): React.CSSProperties {
  return {
    position: 'absolute',
    top: '50%',
    transform: 'translateY(-50%)',
    [side]: '12px',
    zIndex: 9,
    width: '40px',
    height: '40px',
    padding: 0,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    border: '1px solid #3a485a',
    borderRadius: '999px',
    cursor: 'pointer',
    color: '#d9ecff',
    fontSize: '22px',
    fontWeight: 700,
    lineHeight: 1,
    background: 'linear-gradient(180deg, #2f3f53 0%, #1c2633 100%)',
  }
}

export default App
