import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

type CameraLocation = {
  id: number
  longitude: number
  latitude: number
  label: string
}

const locations: CameraLocation[] = [
  { id: 1, longitude: -75.754, latitude: 39.68, label: 'Camera 1' },
  { id: 2, longitude: -75.756, latitude: 39.682, label: 'Camera 2' },
  { id: 3, longitude: -75.7525923185931, latitude: 39.6805956047935, label: 'Camera 3' },
  { id: 4, longitude: -75.74838725868372, latitude: 39.67713476915951, label: 'Camera 4' },
  { id: 5, longitude: -75.75016194351606, latitude: 39.67656997674862, label: 'Camera 5' },
  { id: 6, longitude: -75.74940763490758, latitude: 39.67758513315677, label: 'Camera 6' },
  { id: 7, longitude: -75.75101222381147, latitude: 39.67938571144765, label: 'Camera 7' },
  { id: 8, longitude: -75.74995908040515, latitude: 39.681231237836215, label: 'Camera 8' },
  { id: 9, longitude: -75.74851252255588, latitude: 39.680870380930635, label: 'Camera 9' },
  { id: 10, longitude: -75.75035782639361, latitude: 39.67531235608384, label: 'Camera 10' },
  { id: 11, longitude: -75.75768872147658, latitude: 39.6896962765708, label: 'Camera 11' },
  { id: 12, longitude: -75.75657717953996, latitude: 39.68935176073996, label: 'Camera 12' },
]

interface LoadMapProps {
  selected?: number
  onSelect?: (id: number) => void
}

export function LoadMap({ selected = locations[0].id, onSelect }: LoadMapProps) {
  return (
    <MapContainer
      center={[39.68053620506273, -75.75408714292978]}
      zoom={16}
      style={{ width: '100%', height: '100%' }}
      scrollWheelZoom
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {locations.map((loc) => (
        <CircleMarker
          key={loc.id}
          center={[loc.latitude, loc.longitude]}
          radius={loc.id === selected ? 14 : 10}
          pathOptions={{
            color: '#dbedff',
            weight: loc.id === selected ? 8 : 6,
            fillColor: '#56a9fc',
            fillOpacity: 1,
          }}
          eventHandlers={{ click: () => onSelect?.(loc.id) }}
        >
          <Tooltip>{loc.label}</Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  )
}
