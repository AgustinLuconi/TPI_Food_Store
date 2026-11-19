import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { Checkbox } from '@/shared/ui/Checkbox'
import { Input } from '@/shared/ui/Input'
import { useGuardarDireccion } from '../hooks/useDirecciones'
import { coordenadasIncompletas, leerPunto } from '../lib/coordenadas'
import type { Direccion, Punto } from '../types'
import { MapaDeUbicacion } from './MapaDeUbicacion'

interface Props {
  /** null = alta; con valor = edición. */
  direccion: Direccion | null
  onClose: () => void
  onSaved: (guardada: Direccion, modo: 'create' | 'edit') => void
}

export function DireccionFormModal({ direccion, onClose, onSaved }: Props) {
  const mode = direccion ? 'edit' : 'create'
  const [alias, setAlias] = useState(direccion?.alias ?? '')
  const [linea1, setLinea1] = useState(direccion?.linea1 ?? '')
  const [linea2, setLinea2] = useState(direccion?.linea2 ?? '')
  const [ciudad, setCiudad] = useState(direccion?.ciudad ?? '')
  const [provincia, setProvincia] = useState(direccion?.provincia ?? '')
  const [cp, setCp] = useState(direccion?.codigo_postal ?? '')
  const [lat, setLat] = useState(direccion?.lat?.toString() ?? '')
  const [lng, setLng] = useState(direccion?.lng?.toString() ?? '')
  const [principal, setPrincipal] = useState(direccion?.es_principal ?? false)
  const [errores, setErrores] = useState<Record<string, string>>({})
  const guardar = useGuardarDireccion()

  const punto = leerPunto(lat, lng)

  function elegirEnElMapa(p: Punto) {
    setLat(String(p.lat))
    setLng(String(p.lng))
  }

  function enviar() {
    const nuevos: Record<string, string> = {}
    if (!linea1.trim()) nuevos.linea1 = 'Ingresá la calle y el número'
    if (coordenadasIncompletas(lat, lng))
      nuevos.coordenadas = 'Completá latitud y longitud, o dejá las dos vacías'
    else if ((lat.trim() || lng.trim()) && !punto)
      nuevos.coordenadas = 'Latitud entre −90 y 90 y longitud entre −180 y 180'
    setErrores(nuevos)
    if (Object.keys(nuevos).length > 0) return
    guardar.mutate(
      {
        id: direccion?.id,
        input: {
          alias: alias.trim() || null,
          linea1: linea1.trim(),
          linea2: linea2.trim() || null,
          ciudad: ciudad.trim() || null,
          provincia: provincia.trim() || null,
          codigo_postal: cp.trim() || null,
          lat: punto?.lat ?? null,
          lng: punto?.lng ?? null,
          es_principal: principal,
        },
      },
      { onSuccess: (guardada) => onSaved(guardada, mode) },
    )
  }

  const error = guardar.error ? toApiError(guardar.error) : null
  const deCampo = (campo: string) => (error?.field === campo ? error.message : undefined)

  return (
    <EntityFormModal
      open
      mode={mode}
      entityName="dirección"
      onClose={onClose}
      onSubmit={enviar}
      isSubmitting={guardar.isPending}
      error={error && !error.field ? error.message : null}
    >
      <Input
        label="Alias"
        maxLength={50}
        placeholder="Casa, Trabajo…"
        value={alias}
        onChange={(e) => setAlias(e.target.value)}
      />
      <Input
        label="Calle y número"
        required
        value={linea1}
        onChange={(e) => setLinea1(e.target.value)}
        error={errores.linea1 ?? deCampo('linea1')}
      />
      <Input
        label="Piso, depto u otra referencia"
        value={linea2}
        onChange={(e) => setLinea2(e.target.value)}
      />
      <div className="grid grid-cols-2 gap-3">
        <Input label="Ciudad" value={ciudad} onChange={(e) => setCiudad(e.target.value)} />
        <Input label="Provincia" value={provincia} onChange={(e) => setProvincia(e.target.value)} />
      </div>
      <Input
        label="Código postal"
        maxLength={20}
        value={cp}
        onChange={(e) => setCp(e.target.value)}
      />

      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-sm font-semibold text-navy-900">Ubicación en el mapa</legend>
        <p className="text-xs text-navy-500">
          Tocá el mapa o arrastrá el marcador. Sin coordenadas no podemos calcular el envío a
          domicilio.
        </p>
        <MapaDeUbicacion value={punto} onChange={elegirEnElMapa} />
        <div className="grid grid-cols-2 gap-3">
          <Input
            label="Latitud"
            inputMode="decimal"
            value={lat}
            onChange={(e) => setLat(e.target.value)}
          />
          <Input
            label="Longitud"
            inputMode="decimal"
            value={lng}
            onChange={(e) => setLng(e.target.value)}
          />
        </div>
        {(errores.coordenadas ?? deCampo('lat')) && (
          <p role="alert" className="text-sm text-danger-700">
            {errores.coordenadas ?? deCampo('lat')}
          </p>
        )}
      </fieldset>
      <Checkbox
        label="Usar como dirección principal"
        checked={principal}
        onChange={(e) => setPrincipal(e.target.checked)}
      />
    </EntityFormModal>
  )
}
