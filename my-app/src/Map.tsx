import L from 'leaflet'
import { useMemo } from 'react'
import { MapContainer, Marker, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import './Map.css'
import type { CamState } from './useBackend'
import { formatEventType } from './useBackend'

type CameraLocation = {
  id: number
  lat: number
  lng: number
  label: string
}

const locations: CameraLocation[] = [
  { id: 0,  lat: 39.68000, lng: -75.75400, label: 'Main Entrance' },
  { id: 1,  lat: 39.68200, lng: -75.75600, label: 'Lobby' },
  { id: 2,  lat: 39.68060, lng: -75.75259, label: 'Parking Lot A' },
  { id: 3,  lat: 39.67713, lng: -75.74839, label: 'Parking Lot B' },
  { id: 4,  lat: 39.67657, lng: -75.75016, label: 'Stairwell North' },
  { id: 5,  lat: 39.67759, lng: -75.74941, label: 'Stairwell South' },
  { id: 6,  lat: 39.67939, lng: -75.75101, label: 'Server Room' },
  { id: 7,  lat: 39.68123, lng: -75.74996, label: 'Loading Dock' },
  { id: 8,  lat: 39.68087, lng: -75.74851, label: 'Rooftop' },
  { id: 9,  lat: 39.67531, lng: -75.75036, label: 'Courtyard' },
  { id: 10, lat: 39.68970, lng: -75.75769, label: 'Side Entrance' },
  { id: 11, lat: 39.68935, lng: -75.75658, label: 'Gymnasium' },
]

interface LoadMapProps {
  selected?: number
  onSelect?: (id: number) => void
  camState?: Record<string, CamState>
}

function CameraMarker({
  loc,
  isSelected,
  state,
  onSelect,
}: {
  loc: CameraLocation
  isSelected: boolean
  state?: CamState
  onSelect?: (id: number) => void
}) {
  const hasThreat = state?.hasThreat ?? false
  const hasActivity = state?.hasActivity ?? false
  const lastEvent = state?.lastEvent

  const icon = useMemo(() => {
    const color = hasThreat ? '#ef4444' : '#22c55e'
    const dotSize = 14

    const borderStyle = isSelected
      ? `box-shadow: 0 0 0 3px #000; border: none;`
      : `border: 2px solid rgba(255,255,255,0.55);`

    const threatClass = hasThreat ? 'map-dot--threat' : ''

    const bubbleHtml = hasThreat && lastEvent
      ? `<div class="map-bubble">
           <span class="map-bubble-text">
             &#x1F6A8; ${formatEventType(lastEvent.event_type)}
             &nbsp;${Math.round(lastEvent.confidence * 100)}%
           </span>
           <span class="map-bubble-arrow"></span>
         </div>`
      : ''

    return L.divIcon({
      className: 'map-marker-host',
      html: `<div class="map-dot-wrap">
               <div class="map-dot ${threatClass}" style="
                 width: ${dotSize}px;
                 height: ${dotSize}px;
                 background: ${color};
                 border-radius: 50%;
                 ${borderStyle}
               "></div>
               ${bubbleHtml}
             </div>`,
      iconSize: [dotSize + 10, dotSize + 10],
      iconAnchor: [(dotSize + 10) / 2, (dotSize + 10) / 2],
    })
  }, [hasThreat, hasActivity, isSelected, lastEvent])

  return (
    <Marker
      position={[loc.lat, loc.lng]}
      icon={icon}
      title={loc.label}
      eventHandlers={{ click: () => onSelect?.(loc.id) }}
    />
  )
}

export function LoadMap({ selected = 0, onSelect, camState }: LoadMapProps) {
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
        <CameraMarker
          key={loc.id}
          loc={loc}
          isSelected={loc.id === selected}
          state={camState?.[`cam_${loc.id}`]}
          onSelect={onSelect}
        />
      ))}
    </MapContainer>
  )
}
