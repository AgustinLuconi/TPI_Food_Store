import type { ReactNode } from 'react'
import { formatearDinero, formatearFecha } from '@/shared/lib/formato'
import { Card } from '@/shared/ui/Card'
import type { Pedido } from '../types'
import { EstadoDelPedido } from './EstadoDelPedido'
import { LineaDeTiempo } from './LineaDeTiempo'
import { PasosDelPedido } from './PasosDelPedido'
import { Totales } from './Totales'

const FORMA_DE_PAGO: Record<string, string> = {
  EFECTIVO: 'Efectivo',
  TRANSFERENCIA: 'Transferencia',
  MERCADOPAGO: 'MercadoPago',
}

/** Todo lo que se ve de un pedido: lo usan el cliente (seguimiento) y el personal (gestión), cada uno con sus acciones. */
export function DetalleDelPedido({
  pedido,
  acciones,
  mostrarCliente = false,
}: {
  pedido: Pedido
  acciones?: ReactNode
  mostrarCliente?: boolean
}) {
  const conEnvio = pedido.direccion_id !== null
  const d = pedido.direccion
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold text-navy-900">Pedido #{pedido.id}</h1>
          <p className="text-sm text-navy-500">
            {formatearFecha(pedido.created_at, true)}
            {mostrarCliente && ` · ${pedido.cliente_nombre}`}
          </p>
        </div>
        <EstadoDelPedido estado={pedido.estado_codigo} conEnvio={conEnvio} />
      </div>

      <PasosDelPedido estado={pedido.estado_codigo} conEnvio={conEnvio} />

      <div className="grid gap-4 md:grid-cols-2">
        <Card className="flex flex-col gap-3">
          <h2 className="font-bold text-navy-900">Tu pedido</h2>
          <ul className="flex flex-col divide-y divide-surface-border">
            {pedido.lineas.map((l) => (
              <li key={l.id} className="flex items-start justify-between gap-3 py-2 text-sm">
                <div>
                  <p className="font-semibold text-navy-900">
                    {l.cantidad} × {l.nombre_snapshot}
                  </p>
                  {l.exclusiones.length > 0 && (
                    <p className="text-navy-500">
                      Sin: {l.exclusiones.map((e) => e.nombre).join(', ')}
                    </p>
                  )}
                </div>
                <p className="font-semibold">{formatearDinero(l.subtotal)}</p>
              </li>
            ))}
          </ul>
          <Totales
            subtotal={pedido.subtotal}
            costoEnvio={pedido.costo_envio}
            total={pedido.total}
          />
        </Card>

        <div className="flex flex-col gap-4">
          <Card className="flex flex-col gap-1 text-sm">
            <h2 className="font-bold text-navy-900">Entrega</h2>
            {d ? (
              <p className="text-navy-700">
                {[d.linea1, d.linea2, d.ciudad, d.provincia].filter(Boolean).join(', ')}
              </p>
            ) : (
              <p className="text-navy-700">Retiro en el local</p>
            )}
            {pedido.notas && <p className="text-navy-500">Notas: {pedido.notas}</p>}
          </Card>
          <Card className="flex flex-col gap-1 text-sm">
            <h2 className="font-bold text-navy-900">Pago</h2>
            <p className="text-navy-700">
              {FORMA_DE_PAGO[pedido.forma_pago_codigo] ?? pedido.forma_pago_codigo}
            </p>
            {pedido.pago ? (
              <p className="font-semibold text-success-600">
                Pago registrado: {formatearDinero(pedido.pago.monto)} el{' '}
                {formatearFecha(pedido.pago.created_at, true)}
              </p>
            ) : pedido.estado_codigo === 'CANCELADO' ? (
              <p className="text-navy-500">El pedido se canceló sin pago.</p>
            ) : (
              <p className="text-navy-500">
                Todavía no se registró el pago. El local lo confirma al recibirlo.
              </p>
            )}
          </Card>
        </div>
      </div>

      <Card className="flex flex-col gap-3">
        <h2 className="font-bold text-navy-900">Historial</h2>
        <LineaDeTiempo historial={pedido.historial} conEnvio={conEnvio} />
      </Card>

      {acciones && <div className="flex flex-wrap gap-3">{acciones}</div>}
    </div>
  )
}
