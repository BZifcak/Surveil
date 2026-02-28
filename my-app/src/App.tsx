import { useState } from 'react'
import './App.css'
import 'leaflet/dist/leaflet.css'
import { LeafletMap } from './Map'

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
    </>
  )
}

export default App