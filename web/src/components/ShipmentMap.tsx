import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

/**
 * Live shipment location on a free OpenStreetMap/Leaflet map (US-9.2) — no API
 * key. A vector CircleMarker avoids Leaflet's default marker-image asset issue
 * under Vite. The marker follows new coordinates as the page polls for updates.
 */
export function ShipmentMap({ lat, lng }: { lat: number; lng: number }) {
  const elRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const markerRef = useRef<L.CircleMarker | null>(null)

  useEffect(() => {
    if (!elRef.current || mapRef.current) return
    const map = L.map(elRef.current).setView([lat, lng], 13)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    markerRef.current = L.circleMarker([lat, lng], {
      radius: 8,
      color: '#1b1c1c',
      weight: 2,
      fillColor: '#0F6B3E',
      fillOpacity: 0.9,
    }).addTo(map)
    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
      markerRef.current = null
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    if (mapRef.current && markerRef.current) {
      markerRef.current.setLatLng([lat, lng])
      mapRef.current.panTo([lat, lng])
    }
  }, [lat, lng])

  return (
    <div
      ref={elRef}
      className="w-full h-[320px] rounded-xl overflow-hidden border border-surface-container-high"
      style={{ zIndex: 0 }}
    />
  )
}
