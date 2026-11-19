import { useState } from 'react'
import { Link } from 'react-router'
import { getErrorMessage } from '@/shared/api/errors'
import { useHoyEnElLocal } from '@/shared/hooks/useEstadoLocal'
import { formatearCantidad, formatearDinero, formatearFecha } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Card } from '@/shared/ui/Card'
import { Select } from '@/shared/ui/Select'
import {
  useColaDePedidos,
  useColaDeProduccion,
  useConteoDePedidos,
  useMermas,
  useResumen,
  useStockBajo,
  useTopProductos,
  useVentas,
} from '../hooks/useDashboard'
import type { FilaDeCola, ItemStockBajo } from '../types'
import { Cargando, KpiCard, Seccion } from './Bloques'
import { GraficoDeMermas, GraficoDeVentas, GraficoPorEstado, GraficoTopProductos } from './Graficos'

const PERIODOS = [
  { value: '7', label: 'Últimos 7 días' },
  { value: '30', label: 'Últimos 30 días' },
  { value: '90', label: 'Últimos 90 días' },
]

function Periodo({
  valor,
  onChange,
  etiqueta,
}: {
  valor: number
  onChange: (n: number) => void
  etiqueta: string
}) {
  return (
    <div className="sm:w-56">
      <Select
        label={etiqueta}
        value={String(valor)}
        options={PERIODOS}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  )
}

const Error = ({ e }: { e: unknown }) => (
  <p role="alert" className="text-sm text-danger-700">
    {getErrorMessage(e)}
  </p>
)

/** ADMIN: ventas del día, ticket promedio, ingresos por período y ranking de productos. */
export function SeccionVentas() {
  const [dias, setDias] = useState(30)
  const resumen = useResumen()
  const ventas = useVentas(dias, useHoyEnElLocal())
  const top = useTopProductos(5)

  return (
    <Seccion titulo="Ventas">
      {resumen.isError ? (
        <Error e={resumen.error} />
      ) : resumen.data ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <KpiCard
            titulo="Ventas de hoy"
            valor={formatearDinero(resumen.data.ventas_del_dia)}
            ayuda={`${resumen.data.pedidos_pagados_del_dia} pedidos con pago aprobado`}
          />
          <KpiCard
            titulo="Ticket promedio"
            valor={formatearDinero(resumen.data.ticket_promedio)}
            ayuda="Promedio de los pedidos pagados de hoy"
          />
          <KpiCard
            titulo="Pedidos de hoy"
            valor={resumen.data.pedidos_del_dia}
            ayuda="Creados hoy, en cualquier estado"
          />
          <KpiCard
            titulo="Stock bajo"
            valor={resumen.data.stock_bajo.productos + resumen.data.stock_bajo.insumos}
            ayuda={`${resumen.data.stock_bajo.productos} productos y ${resumen.data.stock_bajo.insumos} insumos`}
          />
        </div>
      ) : (
        <Cargando alto="h-24" />
      )}
      <Periodo valor={dias} onChange={setDias} etiqueta="Período de ingresos" />
      <div className="grid gap-4 lg:grid-cols-2">
        {ventas.data ? (
          <GraficoDeVentas serie={ventas.data.serie} total={ventas.data.total} />
        ) : ventas.isError ? (
          <Error e={ventas.error} />
        ) : (
          <Cargando />
        )}
        {top.data ? (
          <GraficoTopProductos productos={top.data} />
        ) : top.isError ? (
          <Error e={top.error} />
        ) : (
          <Cargando />
        )}
      </div>
    </Seccion>
  )
}

/** ADMIN: pedidos y pagos por estado, calculados en la base. */
export function SeccionPedidosAdmin() {
  const resumen = useResumen()
  return (
    <Seccion titulo="Pedidos y pagos">
      {resumen.data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <GraficoPorEstado
            titulo="Pedidos por estado"
            datos={resumen.data.pedidos_por_estado}
            descripcion="Cantidad de pedidos en cada estado."
          />
          <GraficoPorEstado
            titulo="Pagos por estado"
            datos={resumen.data.pagos_por_estado}
            descripcion="Cantidad de pagos por estado de pago."
          />
        </div>
      ) : resumen.isError ? (
        <Error e={resumen.error} />
      ) : (
        <Cargando />
      )}
      <p>
        <Link to={RUTAS.adminPedidos} className="font-semibold text-accent-700 underline">
          Ir a la gestión de pedidos
        </Link>
      </p>
    </Seccion>
  )
}

const ESTADOS_DE_LA_COLA = ['PENDIENTE', 'CONFIRMADO', 'EN_PREPARACION', 'EN_CAMINO'] as const
const NOMBRE: Record<string, string> = {
  PENDIENTE: 'Pendientes de pago',
  CONFIRMADO: 'Confirmados',
  EN_PREPARACION: 'En preparación',
  EN_CAMINO: 'En camino / listos',
}

/** PEDIDOS: pedidos por estado y cola de preparación. */
export function SeccionPedidosPersonal() {
  const conteos = useConteoDePedidos([...ESTADOS_DE_LA_COLA])
  return (
    <Seccion titulo="Pedidos">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {ESTADOS_DE_LA_COLA.map((e, i) => (
          <Link
            key={e}
            to={`${RUTAS.adminPedidos}?estado=${e}`}
            aria-label={`${NOMBRE[e]}: ver los pedidos`}
          >
            <KpiCard titulo={NOMBRE[e]} valor={conteos[i].data ?? '…'} ayuda="Ver el listado" />
          </Link>
        ))}
      </div>
      <h3 className="font-bold text-navy-900">Cola de preparación</h3>
      <div className="grid gap-4 md:grid-cols-2">
        <Cola
          titulo="Por preparar (confirmados)"
          consulta={useColaDePedidos('CONFIRMADO')}
          href={(f) => RUTAS.adminPedido(f.id)}
          vacio="No hay pedidos esperando."
        />
        <Cola
          titulo="En preparación"
          consulta={useColaDePedidos('EN_PREPARACION')}
          href={(f) => RUTAS.adminPedido(f.id)}
          vacio="Nada en preparación."
        />
      </div>
    </Seccion>
  )
}

/** STOCK y ADMIN: productos e insumos bajo el mínimo y lotes que vencen pronto. */
export function SeccionStock() {
  const [dias, setDias] = useState(7)
  const stock = useStockBajo(dias)
  return (
    <Seccion titulo="Stock">
      {stock.isError ? (
        <Error e={stock.error} />
      ) : !stock.data ? (
        <Cargando />
      ) : (
        <div className="grid gap-4 lg:grid-cols-2">
          <TablaDeStock
            titulo="Productos bajo el mínimo"
            filas={stock.data.productos}
            vacio="Todos los productos están por encima del mínimo."
          />
          <TablaDeStock
            titulo="Insumos bajo el mínimo"
            filas={stock.data.insumos}
            vacio="Todos los insumos están por encima del mínimo."
          />
          <Card className="flex flex-col gap-3 lg:col-span-2">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <h3 className="font-bold text-navy-900">Lotes por vencer</h3>
              <div className="sm:w-56">
                <Select
                  label="Vencen en los próximos"
                  value={String(dias)}
                  options={[
                    { value: '3', label: '3 días' },
                    { value: '7', label: '7 días' },
                    { value: '15', label: '15 días' },
                    { value: '30', label: '30 días' },
                  ]}
                  onChange={(e) => setDias(Number(e.target.value))}
                />
              </div>
            </div>
            {stock.data.lotes_por_vencer.length === 0 ? (
              <p className="text-sm text-navy-500">
                No hay lotes con stock que venzan en ese plazo.
              </p>
            ) : (
              <ul className="flex flex-col divide-y divide-surface-border text-sm">
                {stock.data.lotes_por_vencer.map((l) => (
                  <li key={l.id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                    <span>
                      <strong>{l.producto_nombre}</strong> · lote {l.codigo_lote} ·{' '}
                      {formatearCantidad(l.stock_real)} u.
                    </span>
                    <span className="flex items-center gap-2">
                      {formatearFecha(l.fecha_vencimiento)}
                      {l.vencido ? (
                        <Badge tone="danger">Vencido</Badge>
                      ) : (
                        <Badge tone={l.dias_restantes <= 2 ? 'accent' : 'neutral'}>
                          {l.dias_restantes} días
                        </Badge>
                      )}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            <Link
              to={RUTAS.adminInventario}
              className="text-sm font-semibold text-accent-700 underline"
            >
              Ir al inventario
            </Link>
          </Card>
        </div>
      )}
    </Seccion>
  )
}

function TablaDeStock({
  titulo,
  filas,
  vacio,
}: {
  titulo: string
  filas: ItemStockBajo[]
  vacio: string
}) {
  return (
    <Card className="flex flex-col gap-3">
      <h3 className="font-bold text-navy-900">{titulo}</h3>
      {filas.length === 0 ? (
        <p className="text-sm text-navy-500">{vacio}</p>
      ) : (
        <div className="max-h-64 overflow-auto">
          <table className="w-full text-left text-sm">
            <caption className="sr-only">{titulo}</caption>
            <thead className="text-xs uppercase text-navy-500">
              <tr>
                <th scope="col" className="py-1">
                  Nombre
                </th>
                <th scope="col" className="py-1">
                  Disponible
                </th>
                <th scope="col" className="py-1">
                  Mínimo
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-surface-border">
              {filas.map((f) => (
                <tr key={f.id}>
                  <td className="py-1.5 font-semibold">{f.nombre}</td>
                  <td className="py-1.5 font-semibold text-danger-700">
                    {formatearCantidad(f.stock_disponible)}
                  </td>
                  <td className="py-1.5">{f.stock_minimo}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

/** STOCK y ADMIN: órdenes de producción en curso. */
export function SeccionProduccion() {
  return (
    <Seccion titulo="Producción">
      <div className="grid gap-4 md:grid-cols-2">
        <Cola
          titulo="Órdenes planificadas"
          consulta={useColaDeProduccion('PLANIFICADA')}
          href={() => RUTAS.adminProduccion}
          vacio="No hay órdenes planificadas."
        />
        <Cola
          titulo="Órdenes en proceso"
          consulta={useColaDeProduccion('EN_PROCESO')}
          href={() => RUTAS.adminProduccion}
          vacio="No hay órdenes en proceso."
        />
      </div>
    </Seccion>
  )
}

/** STOCK y ADMIN: mermas por motivo, separadas en productos e insumos (sus unidades no se pueden sumar). */
export function SeccionMermas() {
  const [dias, setDias] = useState(30)
  const mermas = useMermas(dias, useHoyEnElLocal())
  return (
    <Seccion titulo="Mermas">
      <Periodo valor={dias} onChange={setDias} etiqueta="Período de mermas" />
      {mermas.data ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <GraficoDeMermas titulo="Mermas de productos" mermas={mermas.data.productos} />
          <GraficoDeMermas titulo="Mermas de insumos" mermas={mermas.data.insumos} />
        </div>
      ) : mermas.isError ? (
        <Error e={mermas.error} />
      ) : (
        <Cargando />
      )}
    </Seccion>
  )
}

function Cola({
  titulo,
  consulta,
  href,
  vacio,
}: {
  titulo: string
  consulta: { data?: { total: number; filas: FilaDeCola[] }; isError: boolean; error: unknown }
  href: (f: FilaDeCola) => string
  vacio: string
}) {
  return (
    <Card className="flex flex-col gap-2">
      <h3 className="font-bold text-navy-900">
        {titulo}{' '}
        {consulta.data && (
          <span className="font-normal text-navy-500">({consulta.data.total})</span>
        )}
      </h3>
      {consulta.isError ? (
        <Error e={consulta.error} />
      ) : !consulta.data ? (
        <Cargando alto="h-16" />
      ) : consulta.data.filas.length === 0 ? (
        <p className="text-sm text-navy-500">{vacio}</p>
      ) : (
        <ul className="flex flex-col divide-y divide-surface-border text-sm">
          {consulta.data.filas.map((f) => (
            <li key={f.id}>
              <Link
                to={href(f)}
                className="flex items-center justify-between gap-2 py-2 hover:underline"
              >
                <span className="font-semibold">{f.titulo}</span>
                <span className="text-navy-500">{f.detalle}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}
