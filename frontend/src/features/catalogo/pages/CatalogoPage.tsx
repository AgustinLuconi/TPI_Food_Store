import { getErrorMessage } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Paginacion } from '@/shared/components/Paginacion'
import { Skeleton } from '@/shared/components/Skeleton'
import { useMaestroFilters } from '@/shared/hooks/useMaestroFilters'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'
import { ProductoCard } from '../components/ProductoCard'
import { useOpcionesDeCategoria, useProductos } from '../hooks/useCatalogo'

const ORDENES = [
  { value: 'nombre:asc', label: 'Nombre (A a Z)' },
  { value: 'precio:asc', label: 'Precio: menor a mayor' },
  { value: 'precio:desc', label: 'Precio: mayor a menor' },
]
const POR_PAGINA = 12

/** Catálogo público: búsqueda con debounce, categoría (con sus subcategorías), orden y paginación en el servidor. */
export default function CatalogoPage() {
  const filtros = useMaestroFilters({ campo: 'nombre', sentido: 'asc' }, POR_PAGINA)
  const { data, isLoading, isError, error } = useProductos(filtros.params)
  const { data: categorias = [] } = useOpcionesDeCategoria()

  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-1">
        <h1 className="text-3xl font-extrabold text-navy-900">Nuestra carta</h1>
        <p className="text-navy-700">
          Elegí lo que quieras y armá tu pedido. Si algo te cae mal, podés pedirlo sin ese
          ingrediente.
        </p>
      </header>

      <form
        role="search"
        aria-label="Filtros del catálogo"
        onSubmit={(e) => e.preventDefault()}
        className="grid gap-4 rounded-xl border border-surface-border bg-white p-4 sm:grid-cols-3"
      >
        <Input
          label="Buscar"
          type="search"
          value={filtros.search}
          placeholder="Buscar por nombre…"
          onChange={(e) => filtros.setSearch(e.target.value)}
        />
        <Select
          label="Categoría"
          value={filtros.grupo}
          options={[
            { value: '', label: 'Todas' },
            ...categorias.map((c) => ({ value: String(c.id), label: c.ruta })),
          ]}
          onChange={(e) => filtros.setGrupo(e.target.value)}
        />
        <Select
          label="Ordenar por"
          value={`${filtros.orden.campo}:${filtros.orden.sentido}`}
          options={ORDENES}
          onChange={(e) => {
            const [campo, sentido] = e.target.value.split(':')
            filtros.fijarOrden({ campo, sentido: sentido as 'asc' | 'desc' })
          }}
        />
      </form>

      {isError ? (
        <p role="alert" className="text-sm text-danger-700">
          {getErrorMessage(error)}
        </p>
      ) : isLoading ? (
        <ul
          className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
          aria-busy="true"
          aria-label="Cargando productos"
        >
          {Array.from({ length: 8 }, (_, i) => (
            <li key={i}>
              <Skeleton className="h-72 w-full rounded-xl" />
            </li>
          ))}
        </ul>
      ) : data && data.items.length > 0 ? (
        <>
          <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {data.items.map((p) => (
              <li key={p.id}>
                <ProductoCard producto={p} />
              </li>
            ))}
          </ul>
          <div className="overflow-hidden rounded-xl border border-surface-border bg-white">
            <Paginacion
              page={data.page}
              pages={data.pages}
              total={data.total}
              onPageChange={filtros.setPage}
            />
          </div>
        </>
      ) : (
        <div className="rounded-xl border border-surface-border bg-white">
          <EstadoVacio
            titulo="No encontramos productos"
            descripcion="Probá con otra búsqueda o con otra categoría."
          />
        </div>
      )}
    </div>
  )
}
