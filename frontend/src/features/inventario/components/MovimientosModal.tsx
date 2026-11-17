import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { Paginacion } from '@/shared/components/Paginacion'
import { formatearCantidad, formatearFecha } from '@/shared/lib/formato'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { Modal } from '@/shared/ui/Modal'
import { Select } from '@/shared/ui/Select'
import { useMovimientos, useRegistrarMovimiento } from '../hooks/useInventario'
import { finDelDiaIso, hoyIso } from '../lib/fechas'
import {
  MOTIVOS_MERMA,
  NOMBRE_MOTIVO,
  NOMBRE_TIPO,
  TIPOS_MANUALES,
  type ItemStock,
  type Movimiento,
  type TipoItem,
  type TipoManual,
  type TipoMovimiento,
} from '../types'

interface Props {
  tipo: TipoItem
  item: ItemStock
  onClose: () => void
}

/** Los tipos que suman; el resto resta. El signo lo aporta el tipo (sección 8.1). */
const SUMAN: TipoMovimiento[] = ['ENTRADA', 'AJUSTE_POSITIVO', 'LIBERACION_RESERVA']
const SOLO_DISPONIBLE: TipoMovimiento[] = ['RESERVA', 'LIBERACION_RESERVA']

function origen(m: Movimiento): string {
  if (m.pedido_id) return `Pedido #${m.pedido_id}`
  if (m.orden_produccion_id) return `Orden #${m.orden_produccion_id}`
  return 'Manual'
}

export function MovimientosModal({ tipo, item, onClose }: Props) {
  const [page, setPage] = useState(1)
  const { data, isLoading } = useMovimientos(tipo, item.id, page)

  const [tipoMov, setTipoMov] = useState<TipoManual>('ENTRADA')
  const [cantidad, setCantidad] = useState('')
  const [motivo, setMotivo] = useState('')
  const [codigoLote, setCodigoLote] = useState('')
  const [vencimiento, setVencimiento] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const registrar = useRegistrarMovimiento(tipo, item.id)

  const columnas: Column<Movimiento>[] = [
    { key: 'fecha', header: 'Fecha', render: (m) => formatearFecha(m.fecha_registro, true) },
    {
      key: 'tipo',
      header: 'Tipo',
      render: (m) => (
        <Badge
          tone={
            SOLO_DISPONIBLE.includes(m.tipo_movimiento)
              ? 'accent'
              : SUMAN.includes(m.tipo_movimiento)
                ? 'success'
                : 'danger'
          }
        >
          {NOMBRE_TIPO[m.tipo_movimiento]}
        </Badge>
      ),
    },
    {
      key: 'cantidad',
      header: 'Cantidad',
      render: (m) =>
        `${SUMAN.includes(m.tipo_movimiento) ? '+' : '−'}${formatearCantidad(m.cantidad)}`,
    },
    {
      key: 'motivo',
      header: 'Motivo',
      render: (m) =>
        m.motivo ? (NOMBRE_MOTIVO[m.motivo as keyof typeof NOMBRE_MOTIVO] ?? m.motivo) : '—',
    },
    { key: 'origen', header: 'Origen', render: origen },
    ...(tipo === 'producto'
      ? [
          {
            key: 'lote',
            header: 'Lote',
            render: (m: Movimiento) => (m.lote_id ? `#${m.lote_id}` : '—'),
          },
        ]
      : []),
  ]

  function enviar() {
    const n = cantidad.trim()
    if (!/^\d+(\.\d{1,3})?$/.test(n) || Number(n) <= 0)
      return setErrorLocal('La cantidad debe ser mayor que 0, con hasta 3 decimales.')
    if (tipoMov === 'MERMA' && !motivo) return setErrorLocal('Una merma exige un motivo.')
    if (!!codigoLote.trim() !== !!vencimiento)
      return setErrorLocal('El lote necesita código y fecha de vencimiento juntos.')
    setErrorLocal(null)
    registrar.mutate(
      {
        tipo_movimiento: tipoMov,
        cantidad: n,
        motivo: motivo.trim() || null,
        ...(tipo === 'producto' && tipoMov === 'ENTRADA' && codigoLote.trim()
          ? { codigo_lote: codigoLote.trim(), fecha_vencimiento: finDelDiaIso(vencimiento) }
          : {}),
      },
      {
        onSuccess: () => {
          setCantidad('')
          setMotivo('')
          setCodigoLote('')
          setVencimiento('')
          setPage(1)
        },
      },
    )
  }

  const errorServidor = registrar.error ? toApiError(registrar.error).message : null
  const conLote = tipo === 'producto' && tipoMov === 'ENTRADA'

  return (
    <Modal
      open
      onClose={onClose}
      title={`Movimientos de ${item.nombre}`}
      wide
      footer={
        <Button variant="secondary" onClick={onClose}>
          Cerrar
        </Button>
      }
    >
      <div className="flex flex-col gap-6">
        <p className="text-sm text-navy-700">
          Stock real <strong>{formatearCantidad(item.stock_real ?? 0)}</strong> · disponible{' '}
          <strong>{formatearCantidad(item.stock_disponible ?? 0)}</strong>. El disponible descuenta
          lo reservado por pedidos y órdenes de producción.
        </p>

        <form
          noValidate
          aria-label="Registrar movimiento manual"
          onSubmit={(e) => {
            e.preventDefault()
            enviar()
          }}
          className="grid gap-3 rounded-lg border border-surface-border p-4 sm:grid-cols-2"
        >
          <h3 className="font-bold text-navy-900 sm:col-span-2">Registrar movimiento</h3>
          <Select
            label="Tipo"
            value={tipoMov}
            options={TIPOS_MANUALES.map((t) => ({ value: t, label: NOMBRE_TIPO[t] }))}
            onChange={(e) => {
              setTipoMov(e.target.value as TipoManual)
              setMotivo('')
            }}
          />
          <Input
            label="Cantidad"
            inputMode="decimal"
            value={cantidad}
            onChange={(e) => setCantidad(e.target.value)}
          />
          {tipoMov === 'MERMA' ? (
            <Select
              label="Motivo de la merma"
              value={motivo}
              options={[
                { value: '', label: 'Elegí un motivo…' },
                ...MOTIVOS_MERMA.map((m) => ({ value: m, label: NOMBRE_MOTIVO[m] })),
              ]}
              onChange={(e) => setMotivo(e.target.value)}
            />
          ) : (
            <Input
              label="Motivo (opcional)"
              maxLength={120}
              value={motivo}
              onChange={(e) => setMotivo(e.target.value)}
            />
          )}
          {conLote && (
            <>
              <Input
                label="Código de lote (opcional)"
                maxLength={50}
                value={codigoLote}
                onChange={(e) => setCodigoLote(e.target.value)}
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
            <p
              role="alert"
              className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700 sm:col-span-2"
            >
              {errorLocal ?? errorServidor}
            </p>
          )}
          <div className="sm:col-span-2">
            <Button type="submit" loading={registrar.isPending}>
              Registrar
            </Button>
          </div>
        </form>

        <div className="overflow-hidden rounded-lg border border-surface-border">
          <DataTable
            columns={columnas}
            rows={data?.items ?? []}
            rowKey={(m) => m.id}
            isLoading={isLoading}
            skeletonRows={4}
            emptyTitle="Sin movimientos"
            emptyDescription="Todavía no hay movimientos registrados."
          />
          {data && (
            <Paginacion
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={setPage}
            />
          )}
        </div>
      </div>
    </Modal>
  )
}
