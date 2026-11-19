import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { useEffect, useRef } from 'react'
import { redondear } from '../lib/coordenadas'
import { CENTRO_POR_DEFECTO, type Punto } from '../types'

interface Props {
  value: Punto | null
  onChange: (punto: Punto) => void
}

/** Marcador propio (un círculo naranja): evita los íconos por defecto de Leaflet, que rompen con los bundlers. */
const ICONO = L.divIcon({
  className: '',
  html: '<span style="display:block;width:22px;height:22px;border-radius:50%;background:#ea580c;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5)"></span>',
  iconSize: [22, 22],
  iconAnchor: [11, 11],
})

/**
 * Mapa de OpenStreetMap (sin API key) para marcar el punto de entrega: un clic o arrastrar el marcador. Los
 * campos de latitud y longitud del formulario son la alternativa accesible por teclado.
 */
export function MapaDeUbicacion({ value, onChange }: Props) {
  const contenedor = useRef<HTMLDivElement>(null)
  const mapa = useRef<L.Map | null>(null)
  const marcador = useRef<L.Marker | null>(null)
  // El callback más reciente sin recrear el mapa en cada render.
  const alCambiar = useRef(onChange)
  alCambiar.current = onChange

  useEffect(() => {
    if (!contenedor.current || mapa.current) return
    const centro = value ?? CENTRO_POR_DEFECTO
    const m = L.map(contenedor.current).setView([centro.lat, centro.lng], value ? 16 : 13)
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>',
    }).addTo(m)
    m.on('click', (e: L.LeafletMouseEvent) =>
      alCambiar.current({ lat: redondear(e.latlng.lat), lng: redondear(e.latlng.lng) }),
    )
    mapa.current = m
    // El mapa se crea dentro de un diálogo que todavía no está visible: Leaflet cree que su contenedor mide 0×0 y los
    // clics se convertirían en coordenadas corridas. Se vuelve a medir cada vez que el contenedor cambia de tamaño.
    const observador = new ResizeObserver(() => m.invalidateSize())
    observador.observe(contenedor.current)
    return () => {
      observador.disconnect()
      m.remove()
      mapa.current = null
      marcador.current = null
    }
    // El mapa se crea una sola vez; el punto se sincroniza en el efecto siguiente.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const m = mapa.current
    if (!m) return
    if (!value) {
      marcador.current?.remove()
      marcador.current = null
      return
    }
    const pos: L.LatLngExpression = [value.lat, value.lng]
    if (marcador.current) marcador.current.setLatLng(pos)
    else {
      const nuevo = L.marker(pos, { icon: ICONO, draggable: true, keyboard: false }).addTo(m)
      nuevo.on('dragend', () => {
        const p = nuevo.getLatLng()
        alCambiar.current({ lat: redondear(p.lat), lng: redondear(p.lng) })
      })
      marcador.current = nuevo
    }
    m.panTo(pos)
  }, [value])

  return (
    <div
      ref={contenedor}
      role="application"
      aria-label="Mapa para marcar el punto de entrega. Si no podés usar el mapa, escribí las coordenadas en los campos de abajo."
      className="h-64 w-full overflow-hidden rounded-lg border border-surface-border"
    />
  )
}
