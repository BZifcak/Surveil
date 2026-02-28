import { useState } from 'react'
import './App.css'
import 'leaflet/dist/leaflet.css'
import { LeafletMap } from './Map'
import { CameraFeed } from './Cams'

function App() {
  const [count, setCount] = useState(0)

  return (
    <>
      <h1>Vite + React</h1>
      <div className="card">
        <button onClick={() => setCount((count) => count + 1)}>
          count is {count}
        </button>
      </div>
      <LeafletMap />
      <div style={{ width: '400px', margin: '0 auto' }}>
      <CameraFeed />
    </div>
    </>
  )
}

export default App