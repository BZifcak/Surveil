import { useState } from 'react'
import './App.css'
import 'leaflet/dist/leaflet.css'
import { LeafletMap } from './Map'
import CameraGrid from './Cams'

const imageModules = import.meta.glob('./cameras/*.{jpg,jpeg,png,webp,gif}', { eager: true })
const images = Object.values(imageModules).map((mod: any) => mod.default)

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
      <div className="App">
        <h1>Security Monitor</h1>
        <CameraGrid cameraCount={12} columns={6} images={images}/>
      </div>
    </>
  )
}

export default App