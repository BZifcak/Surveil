import Map from 'react-map-gl/mapbox'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN

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
