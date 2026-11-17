import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { formatearCantidad, formatearFecha } from '@/shared/lib/formato'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { Modal } from '@/shared/ui/Modal'
import { Select } from '@/shared/ui/Select'
import { Spinner } from '@/shared/ui/Spinner'
import {
  useCancelarOrden,
  useCompletarOrden,
  useCrearOrden,
  useOpciones,
  useOrden,
} from '../hooks/useInventario'
import { finDelDiaIso, hoyIso } from '../lib/fechas'
import type { EstadoOrden, Orden } from '../types'

export const TONO_ESTADO: Record<EstadoOrden, 'neutral' | 'accent' | 'success' | 'danger'> = {
  PLANIFICADA: 'neutral',
  EN_PROCESO: 'accent',
  COMPLETADA: 'success',
  CANCELADA: 'danger',
}

interface BaseProps<T = Orden> {
  onClose: () => void
  onDone: (orden: T) => void
}

/** Planificar: crea la orden y reserva los insumos de la receta. Si falta alguno, el servidor responde 409. */
export function OrdenFormModal({ onClose, onDone }: BaseProps) {
  const [destino, setDestino] = useState<'producto' | 'ingrediente'>('producto')
  const [itemId, setItemId] = useState('')
  const [cantidad, setCantidad] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const { data: opciones = [] } = useOpciones(
    destino === 'producto' ? 'producto' : 'ingrediente',
    destino === 'ingrediente',
  )
  const crear = useCrearOrden()

  function enviar() {
    if (!itemId) return setErrorLocal('Elegí qué vas a producir.')
    const n = cantidad.trim()
    if (!/^\d+(\.\d{1,3})?$/.test(n) || Number(n) <= 0)
      return setErrorLocal('La cantidad debe ser mayor que 0, con hasta 3 decimales.')
    setErrorLocal(null)
    crear.mutate(
      destino === 'producto'
        ? { producto_id: Number(itemId), cantidad_a_producir: n }
        : { ingrediente_id: Number(itemId), cantidad_a_producir: n },
      { onSuccess: onDone },
    )
  }
  const errorServidor = crear.error ? toApiError(crear.error).message : null

  return (
    <Modal
      open
      onClose={onClose}
      title="Planificar orden de producción"
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={crear.isPending}>
            Cancelar
          </Button>
          <Button type="submit" form="form-orden" loading={crear.isPending}>
            Planificar
          </Button>
        </>
      }
    >
      <form
        id="form-orden"
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="flex flex-col gap-4"
      >
        <Select
          label="Qué se produce"
          value={destino}
          options={[
            { value: 'producto', label: 'Un producto terminado' },
            { value: 'ingrediente', label: 'Un ingrediente elaborado (sub-ensamble)' },
          ]}
          onChange={(e) => {
            setDestino(e.target.value as 'producto' | 'ingrediente')
            setItemId('')
          }}
        />
        <Select
          label={destino === 'producto' ? 'Producto' : 'Ingrediente elaborado'}
          value={itemId}
          options={[
            { value: '', label: 'Elegí uno…' },
            ...opciones.map((o) => ({ value: String(o.id), label: o.nombre })),
          ]}
          onChange={(e) => setItemId(e.target.value)}
        />
        <Input
          label="Cantidad a producir"
          inputMode="decimal"
          value={cantidad}
          onChange={(e) => setCantidad(e.target.value)}
        />
        <p className="text-sm text-navy-500">
          Al planificar se reservan los insumos de la receta (receta × cantidad). El stock real no
          cambia hasta completar la orden.
        </p>
        {(errorLocal ?? errorServidor) && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {errorLocal ?? errorServidor}
          </p>
        )}
      </form>
    </Modal>
  )
}

/** Completar: libera y consume los insumos y da de alta el resultado. Un producto puede registrarse con lote. */
export function CompletarModal({ orden, onClose, onDone }: BaseProps & { orden: Orden }) {
  const [codigo, setCodigo] = useState('')
  const [vencimiento, setVencimiento] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const completar = useCompletarOrden()
  const esProducto = orden.producto_id !== null

  function enviar() {
    if (!!codigo.trim() !== !!vencimiento)
      return setErrorLocal('El lote necesita código y fecha de vencimiento juntos.')
    setErrorLocal(null)
    completar.mutate(
      {
        id: orden.id,
        lote: codigo.trim()
          ? { codigo_lote: codigo.trim(), fecha_vencimiento: finDelDiaIso(vencimiento) }
          : undefined,
      },
      { onSuccess: onDone },
    )
  }
  const errorServidor = completar.error ? toApiError(completar.error).message : null

  return (
    <Modal
      open
      onClose={onClose}
      title={`Completar orden #${orden.id}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={completar.isPending}>
            Cancelar
          </Button>
          <Button type="submit" form="form-completar" loading={completar.isPending}>
            Completar
          </Button>
        </>
      }
    >
      <form
        id="form-completar"
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="flex flex-col gap-4"
      >
        <p className="text-sm text-navy-700">
          Se consumen los insumos reservados y entran {formatearCantidad(orden.cantidad_a_producir)}{' '}
          de <strong>{orden.nombre}</strong> al stock.
        </p>
        {esProducto && (
          <>
            <Input
              label="Código de lote (opcional)"
              maxLength={50}
              value={codigo}
              onChange={(e) => setCodigo(e.target.value)}
            />
            <Input
              label="Vencimiento del lote"
              type="date"
              min={hoyIso()}
              value={vencimiento}
              onChange={(e) => setVencimiento(e.target.value)}
            />
          </>
        )}
        {(errorLocal ?? errorServidor) && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {errorLocal ?? errorServidor}
          </p>
        )}
      </form>
    </Modal>
  )
}

/** Cancelar exige motivo; libera la reserva de los insumos y el stock real nunca se toca. */
export function CancelarOrdenModal({ orden, onClose, onDone }: BaseProps & { orden: Orden }) {
  const [motivo, setMotivo] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const cancelar = useCancelarOrden()

  function enviar() {
    if (!motivo.trim()) return setErrorLocal('Ingresá el motivo de la cancelación.')
    setErrorLocal(null)
    cancelar.mutate({ id: orden.id, motivo: motivo.trim() }, { onSuccess: onDone })
  }
  const errorServidor = cancelar.error ? toApiError(cancelar.error).message : null

  return (
    <Modal
      open
      onClose={onClose}
      title={`Cancelar orden #${orden.id}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={cancelar.isPending}>
            Volver
          </Button>
          <Button
            type="submit"
            form="form-cancelar-orden"
            variant="danger"
            loading={cancelar.isPending}
          >
            Cancelar orden
          </Button>
        </>
      }
    >
      <form
        id="form-cancelar-orden"
        noValidate
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="flex flex-col gap-4"
      >
        <Input
          label="Motivo de la cancelación"
          required
          maxLength={200}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        {(errorLocal ?? errorServidor) && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {errorLocal ?? errorServidor}
          </p>
        )}
      </form>
    </Modal>
  )
}

/** Detalle: qué se produce y qué insumos consume (calculados al planificar). */
export function DetalleOrdenModal({ id, onClose }: { id: number; onClose: () => void }) {
  const { data, isLoading } = useOrden(id)
  return (
    <Modal
      open
      onClose={onClose}
      title={`Orden #${id}`}
      footer={
        <Button variant="secondary" onClick={onClose}>
          Cerrar
        </Button>
      }
    >
      {isLoading && (
        <div className="flex justify-center py-6">
          <Spinner />
        </div>
      )}
      {data && (
        <div className="flex flex-col gap-4">
          <p className="text-sm">
            <strong>{formatearCantidad(data.cantidad_a_producir)}</strong> de{' '}
            <strong>{data.nombre}</strong>{' '}
            <Badge tone={TONO_ESTADO[data.estado]}>{data.estado}</Badge>
          </p>
          <p className="text-xs text-navy-500">Creada el {formatearFecha(data.created_at, true)}</p>
          {data.motivo_cancelacion && (
            <p className="text-sm">Motivo de la cancelación: {data.motivo_cancelacion}</p>
          )}
          <table className="w-full text-left text-sm">
            <caption className="mb-2 text-left font-bold text-navy-900">
              Insumos que consume
            </caption>
            <thead className="text-xs uppercase text-navy-500">
              <tr>
                <th scope="col" className="py-1">
                  Insumo
                </th>
                <th scope="col" className="py-1 text-right">
                  Cantidad
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {data.componentes.map((c) => (
                <tr key={c.ingrediente_id}>
                  <td className="py-1.5">{c.nombre}</td>
                  <td className="py-1.5 text-right">
                    {formatearCantidad(c.cantidad)} {c.unidad_medida ?? ''}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  )
}
