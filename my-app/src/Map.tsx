import Map, {Marker, Popup} from 'react-map-gl/mapbox'
import { useState } from 'react'
import 'mapbox-gl/dist/mapbox-gl.css'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN

const locations = [
  { id: 1, longitude: -75.754, latitude: 39.680, label: 'Camera 1' },
  { id: 2, longitude: -75.756, latitude: 39.682, label: 'Camera 2' },
]

export function LoadMap() {
  const [selected, setSelected] = useState<number | null>(locations[0].id)
    return (
    <Map
      initialViewState={{
        longitude: -75.75408714292978,
        latitude: 39.68053620506273,
        zoom: 16
      }}
      style={{ width: '80vh', height: '80vh' }}
      mapStyle="mapbox://styles/mapbox/dark-v11"
      mapboxAccessToken={MAPBOX_TOKEN}
    >
      {locations.map(loc => (
        <Marker 
          key={loc.id}
          longitude={loc.longitude}
          latitude={loc.latitude}
          anchor="bottom" 
        >
          <div 
          key={loc.id === selected ? 'selected' : 'unselected'}
          style={{
            backgroundColor: '#56a9fc',
            borderRadius: '50%',
            cursor: 'pointer',
            transition: 'all 0.5s ease',
            ...(loc.id === selected? {width : '15px', height:'15px',border:'15px solid #dbedff'} : { width: '10px', height: '10px', border: '10px solid #dbedff' })
        }}
        onClick={(e :React.MouseEvent) => {e.stopPropagation(); setSelected(loc.id);console.log("selected = " , selected, " cam clicked = ", loc.id);}}
          />
        </Marker>
      ))}
    </Map>
  )
}
