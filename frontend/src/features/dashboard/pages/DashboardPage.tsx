import { useAuthStore } from '@/store/authStore'
import {
  SeccionMermas,
  SeccionPedidosAdmin,
  SeccionPedidosPersonal,
  SeccionProduccion,
  SeccionStock,
  SeccionVentas,
} from '../components/Secciones'

/**
 * Panel de métricas según el rol (sección 11.6): el ADMIN ve todo; PEDIDOS, los pedidos por estado y la cola de
 * preparación; STOCK, el stock bajo, los lotes por vencer, las mermas y la producción. El backend valida cada endpoint.
 */
export default function DashboardPage() {
  const esAdmin = useAuthStore((s) => s.hasRole('ADMIN'))
  const esStock = useAuthStore((s) => s.hasRole('STOCK'))
  const esPedidos = useAuthStore((s) => s.hasRole('PEDIDOS'))

  return (
    <div className="flex flex-col gap-8">
      {esAdmin && (
        <>
          <SeccionVentas />
          <SeccionPedidosAdmin />
        </>
      )}
      {!esAdmin && esPedidos && <SeccionPedidosPersonal />}
      {(esAdmin || esStock) && (
        <>
          <SeccionStock />
          <SeccionProduccion />
        </>
      )}
      {esStock && !esAdmin && <SeccionMermas />}
      {esAdmin && <SeccionMermas />}
    </div>
  )
}
