import { useEffect, useState } from 'react'
import './App.css'
import { LoadMap } from './Map'
import CameraGrid from './Cams'
import Log from './Log'
import { useBackend } from './useBackend'
import * as Tooltip from '@radix-ui/react-tooltip'

type Mode = 'cam' | 'split' | 'log'

const SHORTCUTS: Record<Mode, string[]> = {
  split: [
    'A  Switch to Split view',
    'D  Switch to Grid view',
    '\u2190 \u2192  Cycle selected camera',
  ],
  cam: [
    'A  Switch to Split view',
    'D  Switch to Grid view',
    '\u2190 \u2192  Cycle selected camera',
  ],
  log: [
    'A  Switch to Split view',
    'D  Switch to Grid view',
  ],
}

function App() {
  const { cameras, camState, eventLog, threatCount } = useBackend()
  const cameraCount = 12
  const [mode, setMode] = useState<Mode>('split')
  const [selected, setSelected] = useState<number>(0)
  const [gridPage, setGridPage] = useState<number>(0)

  const shiftCamera = (delta: number) => {
    setSelected((current) => {
      return ((current + delta) % cameraCount + cameraCount) % cameraCount
    })
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

      if (event.key.toLowerCase() === 'a') {
        event.preventDefault()
        setMode('split')
        return
      }

      if (event.key.toLowerCase() === 'd') {
        event.preventDefault()
        setMode('cam')
        return
      }

      if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
        event.preventDefault()
        shiftCamera(-1)
      } else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
        event.preventDefault()
        shiftCamera(1)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [mode])

  return (
    <Tooltip.Provider delayDuration={200}>
      <div style={{ display: 'flex', flexDirection: 'column', width: '100%', height: '100vh', margin: 0, minWidth: 0 }}>
        {/* Navbar */}
        <nav className="app-navbar">
          <button onClick={() => setMode('split')} className={`app-nav-btn ${mode === 'split' ? 'app-nav-btn--active' : ''}`}>Split</button>
          <button onClick={() => setMode('cam')} className={`app-nav-btn ${mode === 'cam' ? 'app-nav-btn--active' : ''}`}>Grid</button>
          <button onClick={() => setMode('log')} className={`app-nav-btn ${mode === 'log' ? 'app-nav-btn--active' : ''}`}>Log</button>

          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <span className="app-hint-icon" tabIndex={-1} aria-label="Keyboard shortcuts" onFocusCapture={(e) => e.stopPropagation()}>
                <svg width="16" height="16" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <rect x="1" y="4" width="14" height="9" rx="1.5" stroke="currentColor" strokeWidth="1.2"/>
                  <rect x="3.5" y="6.5" width="2" height="1.5" rx="0.3" fill="currentColor"/>
                  <rect x="7" y="6.5" width="2" height="1.5" rx="0.3" fill="currentColor"/>
                  <rect x="10.5" y="6.5" width="2" height="1.5" rx="0.3" fill="currentColor"/>
                  <rect x="4.5" y="9.5" width="7" height="1.5" rx="0.3" fill="currentColor"/>
                </svg>
              </span>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content className="app-tooltip" sideOffset={8} side="bottom">
                <div className="app-tooltip-title">Keyboard shortcuts</div>
                {SHORTCUTS[mode].map((line) => (
                  <div key={line} className="app-tooltip-row">
                    <kbd className="app-tooltip-key">{line.split('  ')[0]}</kbd>
                    <span>{line.split('  ')[1]}</span>
                  </div>
                ))}
                <Tooltip.Arrow className="app-tooltip-arrow" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>

          {/* Threat counter — right side */}
          {threatCount > 0 && (
            <span className="app-threat-badge">
              <span style={{ fontSize: '14px' }}>&#x26A0;</span>
              {threatCount}
            </span>
          )}
        </nav>

        {/* Content */}
        <div style={{ display: 'flex', flex: 1, overflow: 'hidden', minWidth: 0 }}>
          {mode === 'split' && (
            <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
              <LoadMap selected={selected} onSelect={setSelected} camState={camState} />
            </div>
          )}

          {mode === 'split' && (
            <div style={{ width: '1px', backgroundColor: '#1a1a1a' }} />
          )}

          {(mode === 'cam' || mode === 'split') && (
            <div style={{ flex: 1, overflow: 'hidden', minWidth: 0, display: 'flex', flexDirection: 'column' }}>
              <div style={{ flex: 1, minHeight: 0 }}>
                <CameraGrid
                  cameraCount={cameraCount}
                  selected={selected}
                  onSelect={setSelected}
                  edgeToEdge={mode === 'split'}
                  camState={camState}
                  apiCameras={cameras}
                  page={gridPage}
                  onPageChange={setGridPage}
                />
              </div>
            </div>
          )}

          {mode === 'log' && (
            <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
              <Log events={eventLog} />
            </div>
          )}
        </div>
      </div>
    </Tooltip.Provider>
  )
}

export default App
