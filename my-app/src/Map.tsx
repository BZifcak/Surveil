import './Map.css'
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

export function LeafletMap() {
  return (
    <MapContainer center={[51.505, -0.09] as [number, number]} zoom={13} style={{ height: '100vh', width: '100%' }}>
      <TileLayer url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      <Marker position={[51.505, -0.09] as [number, number]}>
        <Popup>A marker!</Popup>
      </Marker>
    </MapContainer>
  )
}
