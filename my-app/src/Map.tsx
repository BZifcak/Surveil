import Map, { Marker } from 'react-map-gl/mapbox'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN

const locations = [
  { id: 1, longitude: -75.754, latitude: 39.680, label: 'Camera 1' },
  { id: 2, longitude: -75.756, latitude: 39.682, label: 'Camera 2' },
  { id: 3, longitude: -75.7525923185931, latitude: 39.6805956047935, label: 'Camera 3'}
]

interface LoadMapProps {
  selected?: number
  onSelect?: (id: number) => void
}

export function LoadMap({ selected = locations[0].id, onSelect }: LoadMapProps) {
  return (
    <Map
      initialViewState={{
        longitude: -75.75408714292978,
        latitude: 39.68053620506273,
        zoom: 16,
      }}
      style={{ width: '80vh', height: '80vh' }}
      mapStyle="mapbox://styles/bmzifcak/cmm6u08z2009a01scgggk0ws5"
      mapboxAccessToken={MAPBOX_TOKEN}
    >
      {locations.map((loc) => (
        <Marker key={loc.id} longitude={loc.longitude} latitude={loc.latitude} anchor="bottom">
          <div
            key={loc.id === selected ? 'selected' : 'unselected'}
            style={{
              backgroundColor: '#56a9fc',
              borderRadius: '50%',
              cursor: 'pointer',
              transition: 'all 0.5s ease',
              ...(loc.id === selected
                ? { width: '15px', height: '15px', border: '15px solid #dbedff' }
                : { width: '10px', height: '10px', border: '10px solid #dbedff' }),
            }}
            onClick={(e: React.MouseEvent) => {
              e.stopPropagation()
              onSelect?.(loc.id)
            }}
          />
        </Marker>
      ))}
    </Map>
  )
}
