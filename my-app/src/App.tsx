import { useState } from 'react'
import './App.css'
import { LoadMap } from './Map'
import CameraGrid from './Cams'
type Mode = 'map' | 'cam' | 'split'

const imageModules = import.meta.glob('./cameras/*.{jpg,jpeg,png,webp,gif}', { eager: true })
const images = Object.values(imageModules).map((mod: any) => mod.default)

function App() {
  const [mode, setMode] = useState<Mode>('split')

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', margin: 0 }}>
      
      {/* Navbar */}
      <nav style={{
        display: 'flex',
        gap: '8px',
        padding: '10px 20px',
        backgroundColor: '#1a1a1a',
        borderBottom: '1px solid #333'
      }}>
        <button onClick={() => setMode('map')} style={btnStyle(mode === 'map')}>Map</button>
        <button onClick={() => setMode('cam')} style={btnStyle(mode === 'cam')}>Camera</button>
        <button onClick={() => setMode('split')} style={btnStyle(mode === 'split')}>Split</button>
      </nav>

      {/* Content */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {(mode === 'map' || mode === 'split') && (
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <LoadMap />
          </div>
        )}

        {mode === 'split' && (
          <div style={{ width: '1px', backgroundColor: '#444' }} />
        )}

        {(mode === 'cam' || mode === 'split') && (
          <div style={{ flex: 1, overflow: 'hidden' }}>
            <CameraFeed />
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

export default App