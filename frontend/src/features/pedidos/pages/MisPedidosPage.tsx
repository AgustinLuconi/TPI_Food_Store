import { useState } from 'react'
import { Link } from 'react-router'
import { getErrorMessage } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Paginacion } from '@/shared/components/Paginacion'
import { Skeleton } from '@/shared/components/Skeleton'
import { formatearDinero, formatearFecha } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Select } from '@/shared/ui/Select'
import { EstadoDelPedido } from '../components/EstadoDelPedido'
import { usePedidos } from '../hooks/usePedidos'
import { NOMBRE_ESTADO } from '../lib/estados'
import { ESTADOS_PEDIDO, type EstadoPedido } from '../types'

/** Mis pedidos: del más reciente al más antiguo, con filtro por estado. */
export default function MisPedidosPage() {
  const [estado, setEstado] = useState<EstadoPedido | ''>('')
  const [page, setPage] = useState(1)
  const { data, isLoading, isError, error } = usePedidos({ estado, page, size: 10 })

  return (
    <div className="flex flex-col gap-4">
      <h1 className="text-2xl font-extrabold text-navy-900">Mis pedidos</h1>
      <div className="sm:w-64">
        <Select
          label="Estado"
          value={estado}
          options={[
            { value: '', label: 'Todos' },
            ...ESTADOS_PEDIDO.map((e) => ({ value: e, label: NOMBRE_ESTADO[e] })),
          ]}
          onChange={(e) => {
            setEstado(e.target.value as EstadoPedido | '')
            setPage(1)
          }}
        />
      </div>
      {isError ? (
        <p role="alert" className="text-sm text-danger-700">
          {getErrorMessage(error)}
        </p>
      ) : isLoading ? (
        <Skeleton className="h-40 w-full rounded-xl" />
      ) : data && data.items.length > 0 ? (
        <>
          <ul className="flex flex-col gap-3">
            {data.items.map((p) => (
              <li key={p.id}>
                <Link
                  to={RUTAS.pedido(p.id)}
                  className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-surface-border bg-white p-4 shadow-sm hover:border-accent-600"
                >
                  <div>
                    <p className="font-bold text-navy-900">Pedido #{p.id}</p>
                    <p className="text-sm text-navy-500">{formatearFecha(p.created_at, true)}</p>
                  </div>
                  <EstadoDelPedido estado={p.estado_codigo} conEnvio={p.con_envio} />
                  <p className="font-extrabold text-navy-900">{formatearDinero(p.total)}</p>
                </Link>
              </li>
            ))}
          </ul>
          <div className="overflow-hidden rounded-xl border border-surface-border bg-white">
            <Paginacion
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={setPage}
            />
          </div>
        </>
      ) : (
        <div className="rounded-xl border border-surface-border bg-white">
          <EstadoVacio
            titulo="Todavía no hiciste pedidos"
            descripcion="Cuando pidas algo, vas a poder seguirlo desde acá."
            accion={
              <Link to={RUTAS.inicio} className="font-semibold text-accent-700 underline">
                Ver la carta
              </Link>
            }
          />
        </div>
      )}
    </div>
  )
}
