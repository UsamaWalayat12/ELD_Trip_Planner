import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

/* ── Fix Leaflet default icon paths in Vite ─────────────────────────────── */
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
})

/* ── Custom colored icon factory ────────────────────────────────────────── */
function makeIcon(color, emoji) {
  return L.divIcon({
    className: '',
    html: `
      <div style="
        background:${color};
        width:32px;height:32px;
        border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);
        border:3px solid white;
        box-shadow:0 2px 8px rgba(0,0,0,0.4);
        display:flex;align-items:center;justify-content:center;
      ">
        <span style="transform:rotate(45deg);font-size:14px;">${emoji}</span>
      </div>`,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -36],
  })
}

const ICONS = {
  current: makeIcon('#22c55e', '🚛'),   // green
  pickup: makeIcon('#f97316', '📦'),   // orange
  dropoff: makeIcon('#ef4444', '🏁'),   // red
  fuel: makeIcon('#eab308', '⛽'),   // yellow
  rest: makeIcon('#a855f7', '🛏'),   // purple
}

/* ── Helper: convert ORS [lng,lat] array → Leaflet [lat,lng] ────────────── */
function toLatLng(coords) {
  return coords.map(([lng, lat]) => [lat, lng])
}

/* ── Segment type → icon key ─────────────────────────────────────────────── */
function segmentIcon(type) {
  if (type === 'FUEL_STOP') return ICONS.fuel
  if (type === 'SLEEPER' || type === 'BREAK') return ICONS.rest
  return null
}

/* ── MapView Component ──────────────────────────────────────────────────── */
export default function MapView({ trip }) {
  const mapRef = useRef(null)
  const mapObj = useRef(null)
  const layersRef = useRef([])

  /* Build / rebuild map whenever trip changes */
  useEffect(() => {
    if (!trip || !mapRef.current) return

    /* Init map once */
    if (!mapObj.current) {
      mapObj.current = L.map(mapRef.current, {
        center: [39.5, -98.35],
        zoom: 4,
        zoomControl: true,
      })
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        maxZoom: 19,
      }).addTo(mapObj.current)
    }

    /* Clear previous layers */
    layersRef.current.forEach(l => mapObj.current.removeLayer(l))
    layersRef.current = []

    const add = (layer) => {
      layer.addTo(mapObj.current)
      layersRef.current.push(layer)
      return layer
    }

    /* ── Route polyline ────────────────────────────────────────────────── */
    const geometry = trip.route_geometry || []
    if (geometry.length > 1) {
      const latlngs = toLatLng(geometry)
      add(L.polyline(latlngs, {
        color: '#6366f1',
        weight: 5,
        opacity: 0.85,
        lineJoin: 'round',
        lineCap: 'round',
      }))
      mapObj.current.fitBounds(L.latLngBounds(latlngs), { padding: [40, 40] })
    }

    /* ── Start / Pickup / Dropoff markers ──────────────────────────────── */
    if (trip.current_lat && trip.current_lng) {
      add(L.marker([trip.current_lat, trip.current_lng], { icon: ICONS.current })
        .bindPopup(`<b>🚛 Current Location</b><br>${trip.current_location}`))
    }
    if (trip.pickup_lat && trip.pickup_lng) {
      add(L.marker([trip.pickup_lat, trip.pickup_lng], { icon: ICONS.pickup })
        .bindPopup(`<b>📦 Pickup</b><br>${trip.pickup_location}`))
    }
    if (trip.dropoff_lat && trip.dropoff_lng) {
      add(L.marker([trip.dropoff_lat, trip.dropoff_lng], { icon: ICONS.dropoff })
        .bindPopup(`<b>🏁 Dropoff</b><br>${trip.dropoff_location}`))
    }

    /* ── Fuel & Rest stop markers from segments ─────────────────────────── */
    const stopSegments = (trip.segments || []).filter(
      s => s.segment_type === 'FUEL_STOP' || s.segment_type === 'SLEEPER' || s.segment_type === 'BREAK'
    )

    /* We approximate lat/lng by interpolating geometry by odometer fraction */
    const totalGeomLen = geometry.length
    const totalMiles = trip.total_distance_miles || 1

    stopSegments.forEach((seg) => {
      const fraction = Math.min(seg.odometer_start / totalMiles, 0.999)
      const idx = Math.floor(fraction * (totalGeomLen - 1))
      const coord = geometry[idx]
      if (!coord) return
      const icon = segmentIcon(seg.segment_type)
      if (!icon) return
      add(L.marker([coord[1], coord[0]], { icon })
        .bindPopup(`<b>${seg.label}</b><br>@ ${seg.odometer_start.toFixed(0)} mi`))
    })

  }, [trip])

  /* Cleanup on unmount */
  useEffect(() => {
    return () => {
      if (mapObj.current) {
        mapObj.current.remove()
        mapObj.current = null
      }
    }
  }, [])

  return (
    <div className="map-container">
      <div ref={mapRef} style={{ height: '100%', width: '100%' }} />
    </div>
  )
}





