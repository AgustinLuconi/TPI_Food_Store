import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { useGuardarZona } from '../hooks/useConfiguracion'
import type { Zona } from '../types'

interface Props {
  zona: Zona | null
  onClose: () => void
  onSaved: (guardada: Zona, modo: 'create' | 'edit') => void
}

interface FilaVertice {
  clave: number
  lat: string
  lng: string
}

let contador = 0
const vacio = (): FilaVertice => ({ clave: ++contador, lat: '', lng: '' })

export function ZonaFormModal({ zona, onClose, onSaved }: Props) {
  const mode = zona ? 'edit' : 'create'
  const [nombre, setNombre] = useState(zona?.nombre ?? '')
  const [base, setBase] = useState(zona?.tarifa_base ?? '0')
  const [porKm, setPorKm] = useState(zona?.tarifa_por_km ?? '0')
  const [minimo, setMinimo] = useState(zona?.pedido_minimo ?? '0')
  const [vertices, setVertices] = useState<FilaVertice[]>(
    zona
      ? zona.poligono.map(([lat, lng]) => ({
          clave: ++contador,
          lat: String(lat),
          lng: String(lng),
        }))
      : [vacio(), vacio(), vacio()],
  )
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const guardar = useGuardarZona()

  function cambiar(clave: number, campo: 'lat' | 'lng', valor: string) {
    setVertices((v) => v.map((f) => (f.clave === clave ? { ...f, [campo]: valor } : f)))
  }

  function enviar() {
    if (!nombre.trim()) return setErrorLocal('Ingresá un nombre.')
    for (const [etiqueta, valor] of [
      ['La tarifa base', base],
      ['La tarifa por km', porKm],
      ['El pedido mínimo', minimo],
    ] as const) {
      if (!/^\d+(\.\d{1,2})?$/.test(valor.trim()))
        return setErrorLocal(`${etiqueta} debe ser un monto válido (hasta 2 decimales).`)
    }
    const puntos = vertices.map((v) => [Number(v.lat), Number(v.lng)] as [number, number])
    if (
      vertices.some(
        (v) =>
          !v.lat.trim() ||
          !v.lng.trim() ||
          Number.isNaN(Number(v.lat)) ||
          Number.isNaN(Number(v.lng)),
      )
    )
      return setErrorLocal('Completá latitud y longitud de cada vértice con números.')
    if (puntos.some(([la, lo]) => Math.abs(la) > 90 || Math.abs(lo) > 180))
      return setErrorLocal('Latitud entre −90 y 90, longitud entre −180 y 180.')
    if (new Set(puntos.map((p) => p.join(','))).size < 3)
      return setErrorLocal('El polígono necesita al menos 3 vértices distintos.')
    setErrorLocal(null)
    guardar.mutate(
      {
        id: zona?.id,
        input: {
          nombre: nombre.trim(),
          poligono: puntos,
          tarifa_base: base.trim(),
          tarifa_por_km: porKm.trim(),
          pedido_minimo: minimo.trim(),
        },
      },
      { onSuccess: (guardada) => onSaved(guardada, mode) },
    )
  }
  const errorServidor = guardar.error ? toApiError(guardar.error).message : null

  return (
    <EntityFormModal
      open
      mode={mode}
      entityName="zona"
      onClose={onClose}
      onSubmit={enviar}
      isSubmitting={guardar.isPending}
      error={errorLocal ?? errorServidor}
    >
      <Input
        label="Nombre"
        required
        maxLength={120}
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
      />
      <div className="grid grid-cols-3 gap-3">
        <Input
          label="Tarifa base"
          inputMode="decimal"
          value={base}
          onChange={(e) => setBase(e.target.value)}
        />
        <Input
          label="Tarifa por km"
          inputMode="decimal"
          value={porKm}
          onChange={(e) => setPorKm(e.target.value)}
        />
        <Input
          label="Pedido mínimo"
          inputMode="decimal"
          value={minimo}
          onChange={(e) => setMinimo(e.target.value)}
        />
      </div>
      <p className="text-xs text-navy-500">
        Costo de envío = tarifa base + distancia en km × tarifa por km. Distancia en línea recta
        desde el local.
      </p>
      <fieldset className="flex flex-col gap-3">
        <legend className="mb-1 text-sm font-semibold text-navy-900">Vértices del polígono</legend>
        {vertices.map((v, i) => (
          <div key={v.clave} className="flex items-end gap-2">
            <Input
              label={`Vértice ${i + 1}: latitud`}
              inputMode="decimal"
              value={v.lat}
              onChange={(e) => cambiar(v.clave, 'lat', e.target.value)}
            />
            <Input
              label={`Vértice ${i + 1}: longitud`}
              inputMode="decimal"
              value={v.lng}
              onChange={(e) => cambiar(v.clave, 'lng', e.target.value)}
            />
            {vertices.length > 3 && (
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setVertices((a) => a.filter((x) => x.clave !== v.clave))}
              >
                Quitar
              </Button>
            )}
          </div>
        ))}
        <div>
          <Button size="sm" variant="secondary" onClick={() => setVertices((a) => [...a, vacio()])}>
            + Agregar vértice
          </Button>
        </div>
      </fieldset>
    </EntityFormModal>
  )
}
