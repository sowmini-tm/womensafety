import { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

type LatLngTuple = [number, number]

type RouteMapProps = {
  center?: LatLngTuple
  startPosition?: LatLngTuple | null
  destinationPosition?: LatLngTuple | null
  userPosition?: LatLngTuple | null
  routeCoordinates?: LatLngTuple[]
  className?: string
}

const DEFAULT_CENTER: LatLngTuple = [12.9716, 77.5946]

/**
 * Minimal Leaflet/OpenStreetMap wrapper — no paid tiles, no extra libraries.
 * Markers are circleMarkers so bundlers need no marker-image asset fixes.
 */
export default function RouteMap({
  center,
  startPosition,
  destinationPosition,
  userPosition,
  routeCoordinates,
  className,
}: RouteMapProps) {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const mapRef = useRef<L.Map | null>(null)
  const layersRef = useRef<L.LayerGroup | null>(null)

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return
    const map = L.map(containerRef.current).setView(center ?? DEFAULT_CENTER, 14)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map)
    layersRef.current = L.layerGroup().addTo(map)
    mapRef.current = map

    return () => {
      map.remove()
      mapRef.current = null
      layersRef.current = null
    }
    // Map instance is created exactly once per mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layers = layersRef.current
    if (!map || !layers) return

    layers.clearLayers()

    if (startPosition) {
      L.circleMarker(startPosition, { radius: 7, color: '#34d399', weight: 2, fillColor: '#059669', fillOpacity: 0.95 })
        .addTo(layers)
        .bindTooltip('Start')
    }
    if (destinationPosition) {
      L.circleMarker(destinationPosition, { radius: 7, color: '#fb7185', weight: 2, fillColor: '#e11d48', fillOpacity: 0.95 })
        .addTo(layers)
        .bindTooltip('Destination')
    }
    if (userPosition) {
      L.circleMarker(userPosition, { radius: 6, color: '#22d3ee', weight: 2, fillColor: '#0891b2', fillOpacity: 0.95 })
        .addTo(layers)
        .bindTooltip('You')
    }

    if (routeCoordinates && routeCoordinates.length > 1) {
      L.polyline(routeCoordinates, { color: '#22d3ee', weight: 5, opacity: 0.85 }).addTo(layers)
      map.fitBounds(L.latLngBounds(routeCoordinates), { padding: [28, 28] })
    } else {
      const focus = userPosition ?? startPosition ?? center
      if (focus) map.setView(focus, 15)
    }
  }, [startPosition, destinationPosition, userPosition, routeCoordinates, center])

  return <div ref={containerRef} className={className ?? 'h-64 w-full'} />
}
