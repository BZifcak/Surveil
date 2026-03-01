import Map, { Marker } from 'react-map-gl/mapbox'
import 'mapbox-gl/dist/mapbox-gl.css'
import { useMemo } from 'react'
import type { CamState } from './useBackend'
import { formatEventType } from './useBackend'

const MAPBOX_TOKEN = import.meta.env.VITE_MAPBOX_TOKEN

type CameraLocation = {
  id: number
  lng: number
  lat: number
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

  const markerStyle = useMemo(() => {
    const color = hasThreat ? '#ef4444' : '#91ff95'

    return {
      width: isSelected ? '15px' : '15px',
      height: isSelected ? '15px' : '15px',
      backgroundColor:color,
      borderRadius: '50%',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      border: isSelected
        ? '2px solid #000000'
        : '2px solid rgb(227, 255, 251)',
      boxShadow: hasThreat ? '0 0 8px #ef4444' : 'none',
    }
  }, [hasThreat, hasActivity, isSelected])

  return (
    <Marker
      longitude={loc.lng}
      latitude={loc.lat}
      anchor="center"
    >
      <div style={{ position: 'relative' }}>
        {/* Threat bubble */}
        {hasThreat && lastEvent && (
          <div style={{
            position: 'absolute',
            bottom: '100%',
            left: '50%',
            transform: 'translateX(-50%)',
            marginBottom: '6px',
            backgroundColor: '#1a1a1a',
            color: '#ef4444',
            borderRadius: '6px',
            padding: '4px 8px',
            fontSize: '11px',
            whiteSpace: 'nowrap',
            border: '1px solid #ef4444',
            pointerEvents: 'none',
          }}>
            🚨 {formatEventType(lastEvent.event_type)} {Math.round(lastEvent.confidence * 100)}%
            {/* Arrow */}
            <div style={{
              position: 'absolute',
              top: '100%',
              left: '50%',
              transform: 'translateX(-50%)',
              width: 0,
              height: 0,
              borderLeft: '5px solid transparent',
              borderRight: '5px solid transparent',
              borderTop: '5px solid #ef4444',
            }} />
          </div>
        )}

        {/* Dot */}
        <div
          style={markerStyle}
          onClick={(e: React.MouseEvent) => {
            e.stopPropagation()
            onSelect?.(loc.id)
          }}
          title={loc.label}
        />
      </div>
    </Marker>
  )
}

export function LoadMap({ selected = 0, onSelect, camState }: LoadMapProps) {
  return (
    <Map
      initialViewState={{
        longitude: -75.75408714292978,
        latitude: 39.68053620506273,
        zoom: 16,
      }}
      style={{ width: '100%', height: '100%' }}
      mapStyle="mapbox://styles/bmzifcak/cmm6u08z2009a01scgggk0ws5"
      mapboxAccessToken={MAPBOX_TOKEN}
    >
      {locations.map((loc) => (
        <CameraMarker
          key={loc.id}
          loc={loc}
          isSelected={loc.id === selected}
          state={camState?.[`cam_${loc.id}`]}
          onSelect={onSelect}
        />
      ))}
    </Map>
  )
}