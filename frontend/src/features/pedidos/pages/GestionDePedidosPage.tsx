import { Link, useSearchParams } from 'react-router'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { Paginacion } from '@/shared/components/Paginacion'
import { formatearDinero, formatearFecha } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'
import { EstadoDelPedido } from '../components/EstadoDelPedido'
import { usePedidosDeGestion } from '../hooks/usePedidos'
import { NOMBRE_ESTADO } from '../lib/estados'
import { ESTADOS_PEDIDO, type EstadoPedido, type PedidoItem } from '../types'

const FORMA: Record<string, string> = {
  EFECTIVO: 'Efectivo',
  TRANSFERENCIA: 'Transferencia',
  MERCADOPAGO: 'MercadoPago',
}

/** Gestión de pedidos del personal. Los filtros viven en la URL (?estado=…): se puede compartir o volver atrás. */
export default function GestionDePedidosPage() {
  const [params, setParams] = useSearchParams()
  const estadoParam = params.get('estado') ?? ''
  const estado = (ESTADOS_PEDIDO as string[]).includes(estadoParam)
    ? (estadoParam as EstadoPedido)
    : ''
  const desde = params.get('desde') ?? ''
  const hasta = params.get('hasta') ?? ''
  const page = Math.max(1, Number(params.get('page')) || 1)
  const rangoInvalido = desde !== '' && hasta !== '' && desde > hasta

  const { data, isLoading, isError, error } = usePedidosDeGestion({
    estado,
    page,
    size: 10,
    desde: rangoInvalido ? '' : desde,
    hasta: rangoInvalido ? '' : hasta,
  })

  /**
   * Parte de la URL ACTUAL, no de los parámetros de este render: dos cambios seguidos (Desde y Hasta) antes de que
   * React vuelva a renderizar harían que el segundo pisara al primero. (La forma funcional de setSearchParams no
   * ayuda: a diferencia de setState, no encola; su argumento es el valor del último render.)
   */
  function cambiar(cambios: Record<string, string>) {
    const siguiente = new URLSearchParams(window.location.search)
    for (const [k, v] of Object.entries(cambios)) {
      if (v) siguiente.set(k, v)
      else siguiente.delete(k)
    }
    if (!('page' in cambios)) siguiente.delete('page') // cualquier filtro vuelve a la primera página
    setParams(siguiente, { replace: true })
  }

  const columnas: Column<PedidoItem>[] = [
    { key: 'id', header: 'Pedido', render: (p) => <span className="font-semibold">#{p.id}</span> },
    { key: 'cliente', header: 'Cliente', render: (p) => p.cliente_nombre },
    {
      key: 'estado',
      header: 'Estado',
      render: (p) => <EstadoDelPedido estado={p.estado_codigo} conEnvio={p.con_envio} />,
    },
    { key: 'entrega', header: 'Entrega', render: (p) => (p.con_envio ? 'Envío' : 'Retiro') },
    {
      key: 'pago',
      header: 'Pago',
      render: (p) => FORMA[p.forma_pago_codigo] ?? p.forma_pago_codigo,
    },
    {
      key: 'total',
      header: 'Total',
      className: 'whitespace-nowrap',
      render: (p) => formatearDinero(p.total),
    },
    { key: 'fecha', header: 'Fecha', render: (p) => formatearFecha(p.created_at, true) },
  ]

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Pedidos</h1>
      <Card className="overflow-hidden p-0">
        <form
          aria-label="Filtros de pedidos"
          onSubmit={(e) => e.preventDefault()}
          className="grid gap-4 border-b border-surface-border p-4 sm:grid-cols-3"
        >
          <Select
            label="Estado"
            value={estado}
            options={[
              { value: '', label: 'Todos' },
              ...ESTADOS_PEDIDO.map((e) => ({ value: e, label: NOMBRE_ESTADO[e] })),
            ]}
            onChange={(e) => cambiar({ estado: e.target.value })}
          />
          <Input
            label="Desde"
            type="date"
            value={desde}
            onChange={(e) => cambiar({ desde: e.target.value })}
          />
          <Input
            label="Hasta"
            type="date"
            value={hasta}
            onChange={(e) => cambiar({ hasta: e.target.value })}
            error={rangoInvalido ? '«Desde» no puede ser posterior a «Hasta»' : undefined}
          />
        </form>
        {isError ? (
          <p role="alert" className="p-6 text-sm text-danger-700">
            {getErrorMessage(error)}
          </p>
        ) : (
          <DataTable
            columns={columnas}
            rows={data?.items ?? []}
            rowKey={(p) => p.id}
            isLoading={isLoading}
            emptyTitle="No hay pedidos"
            emptyDescription="Probá con otros filtros."
            actions={(p) => (
              <Link to={RUTAS.adminPedido(p.id)}>
                <Button size="sm" variant="secondary" aria-label={`Ver el pedido ${p.id}`}>
                  Ver
                </Button>
              </Link>
            )}
          />
        )}
        {data && (
          <Paginacion
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={(n) => cambiar({ page: String(n) })}
          />
        )}
      </Card>
    </div>
  )
}
