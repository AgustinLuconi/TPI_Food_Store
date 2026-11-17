import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { formatearFecha } from '@/shared/lib/formato'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Input } from '@/shared/ui/Input'
import { Spinner } from '@/shared/ui/Spinner'
import { useEstadoLocal, useGuardarLocal, useLocal } from '../hooks/useConfiguracion'
import type { Local } from '../types'

const ZONAS = typeof Intl.supportedValuesOf === 'function' ? Intl.supportedValuesOf('timeZone') : []

export function LocalPanel({ onSaved }: { onSaved: () => void }) {
  const { data, isLoading, isError } = useLocal()
  const { data: estado } = useEstadoLocal()
  if (isLoading) return <Spinner />
  if (isError || !data)
    return (
      <p role="alert" className="text-sm text-danger-700">
        No se pudo cargar el local.
      </p>
    )
  return (
    <div className="flex flex-col gap-4">
      {estado && (
        <Card className="flex flex-wrap items-center gap-3">
          <Badge tone={estado.abierto ? 'success' : 'danger'}>
            {estado.abierto ? 'Abierto ahora' : 'Cerrado ahora'}
          </Badge>
          <span className="text-sm text-navy-700">
            {estado.abierto
              ? `Hora del local según ${estado.zona_horaria}.`
              : estado.proxima_apertura
                ? `Próxima apertura: ${formatearFecha(estado.proxima_apertura, true)}.`
                : 'No hay una próxima apertura configurada.'}
          </span>
        </Card>
      )}
      <Formulario local={data} onSaved={onSaved} />
    </div>
  )
}

function Formulario({ local, onSaved }: { local: Local; onSaved: () => void }) {
  const [nombre, setNombre] = useState(local.nombre)
  const [zona, setZona] = useState(local.zona_horaria)
  const [direccion, setDireccion] = useState(local.direccion_origen ?? '')
  const [lat, setLat] = useState(local.lat_origen?.toString() ?? '')
  const [lng, setLng] = useState(local.lng_origen?.toString() ?? '')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const guardar = useGuardarLocal()

  function enviar() {
    if (!nombre.trim()) return setErrorLocal('Ingresá el nombre del local.')
    if (!zona.trim())
      return setErrorLocal('Ingresá la zona horaria (por ejemplo, America/Argentina/Buenos_Aires).')
    if (!!lat.trim() !== !!lng.trim())
      return setErrorLocal('El punto de origen necesita latitud y longitud juntas.')
    const nLat = lat.trim() ? Number(lat) : null
    const nLng = lng.trim() ? Number(lng) : null
    if (
      (nLat !== null && (Number.isNaN(nLat) || Math.abs(nLat) > 90)) ||
      (nLng !== null && (Number.isNaN(nLng) || Math.abs(nLng) > 180))
    )
      return setErrorLocal('Latitud entre −90 y 90, longitud entre −180 y 180.')
    setErrorLocal(null)
    guardar.mutate(
      {
        nombre: nombre.trim(),
        zona_horaria: zona.trim(),
        direccion_origen: direccion.trim() || null,
        lat_origen: nLat,
        lng_origen: nLng,
      },
      { onSuccess: onSaved },
    )
  }
  const errorServidor = guardar.error ? toApiError(guardar.error).message : null

  return (
    <Card>
      <form
        noValidate
        aria-label="Datos del local"
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="grid gap-4 sm:grid-cols-2"
      >
        <datalist id="zonas-horarias">
          {ZONAS.map((z) => (
            <option key={z} value={z} />
          ))}
        </datalist>
        <Input
          label="Nombre del local"
          required
          maxLength={120}
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
        />
        <Input
          label="Zona horaria"
          required
          list="zonas-horarias"
          value={zona}
          onChange={(e) => setZona(e.target.value)}
          hint="Los horarios y el estado abierto/cerrado se evalúan en esta zona."
        />
        <div className="sm:col-span-2">
          <Input
            label="Dirección de origen"
            value={direccion}
            onChange={(e) => setDireccion(e.target.value)}
          />
        </div>
        <Input
          label="Latitud del origen"
          inputMode="decimal"
          value={lat}
          onChange={(e) => setLat(e.target.value)}
          hint="Desde acá se mide la distancia del envío."
        />
        <Input
          label="Longitud del origen"
          inputMode="decimal"
          value={lng}
          onChange={(e) => setLng(e.target.value)}
        />
        {(errorLocal ?? errorServidor) && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700 sm:col-span-2"
          >
            {errorLocal ?? errorServidor}
          </p>
        )}
        <div className="sm:col-span-2">
          <Button type="submit" loading={guardar.isPending}>
            Guardar cambios
          </Button>
        </div>
      </form>
    </Card>
  )
}
