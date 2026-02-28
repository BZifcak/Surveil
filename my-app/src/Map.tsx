import Map from 'react-map-gl/mapbox'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = 'pk.eyJ1IjoiYm16aWZjYWsiLCJhIjoiY21tNnB2OHhqMGtuNjJwcTNpZXcxeTBpZyJ9.vAvY5WflQsy8HPlbRnxViw'

export function LoadMap() {
  return (
    <Map
      initialViewState={{
        //39.68053620506273, -75.75408714292978
        longitude:  -75.75408714292978,
        latitude:39.68053620506273,
        zoom: 16
      }}
      style={{ width: '100vh', height: '100vh' }}
      mapStyle="mapbox://styles/mapbox/dark-v11"
      mapboxAccessToken={MAPBOX_TOKEN}
    />
  )
}
