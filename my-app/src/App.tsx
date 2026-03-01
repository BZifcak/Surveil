import { useState } from 'react'
import './App.css'
import { LoadMap } from './Map'
import CameraGrid from './Cams'

type Mode =  'cam' | 'split'

const imageModules = import.meta.glob<{ default: string }>('./images/*.{jpg,jpeg,png,webp,gif}', { eager: true })
const images = Object.values(imageModules).map((mod) => mod.default)

function App() {
  const cameraCount = 12
  const [mode, setMode] = useState<Mode>('split')
  const [selected, setSelected] = useState<number>(1)
  const [cameraSelectorOpen, setCameraSelectorOpen] = useState<boolean>(false)

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

  return (
    <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100vh', margin: 0, minWidth: 0 }}>
      {/* Navbar */}
      <nav style={{
        position: 'relative',
        display: 'flex',
        gap: '8px',
        padding: '10px 20px',
        backgroundColor: '#1a1a1a',
        borderBottom: '1px solid #333'
      }}>
        <button onClick={() => setModeAndCloseSelector('split')} style={btnStyle(mode === 'split')}>Split</button>
        <button onClick={() => setModeAndCloseSelector('cam')} style={btnStyle(mode === 'cam')}>Camera</button>
        {mode === 'cam' && (
          <button
            onClick={() => setCameraSelectorOpen((open) => !open)}
            style={{
              ...btnStyle(cameraSelectorOpen),
              position: 'absolute',
              left: '50%',
              transform: 'translateX(-50%)',
            }}
          >
            Cameras
          </button>
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
            <button
              onClick={() => shiftCamera(-1)}
              style={arrowBtnStyle('left')}
              aria-label="Previous camera"
            >
              ←
            </button>
            <button
              onClick={() => shiftCamera(1)}
              style={arrowBtnStyle('right')}
              aria-label="Next camera"
            >
              →
            </button>
            {mode === 'split' && (
              <div style={{
                position: 'absolute',
                top: '10px',
                left: '50%',
                transform: 'translateX(-50%)',
                zIndex: 9,
              }}>
                <button
                  onClick={() => setCameraSelectorOpen((open) => !open)}
                  style={btnStyle(cameraSelectorOpen)}
                >
                  Cameras
        </button>
      </div>
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
