import { useState } from 'react'
import { useDebounce } from '@/shared/hooks/useDebounce'
import type { EstadoFiltro, Orden } from '@/shared/types/common'
import type { ListParams } from '../types'

const TAMANO_PAGINA = 10

/**
 * Estado de filtros compartido por todas las pantallas de maestros (sección 11.5):
 * búsqueda con debounce, combo de agrupación (rol, categoría), estado (Activos por defecto),
 * orden en el servidor y página. Cualquier cambio de filtro u orden vuelve a la primera página.
 */
export function useMaestroFilters(ordenInicial: Orden = { campo: 'nombre', sentido: 'asc' }) {
  const [search, setSearchState] = useState('')
  const [estado, setEstadoState] = useState<EstadoFiltro>('activos')
  const [grupo, setGrupoState] = useState('')
  const [orden, setOrden] = useState<Orden>(ordenInicial)
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounce(search, 400)

  const params: ListParams = {
    search: debouncedSearch.trim(),
    estado,
    page,
    size: TAMANO_PAGINA,
    grupo: grupo || undefined,
    orden,
  }

  return {
    params,
    search,
    estado,
    grupo,
    orden,
    page,
    setSearch: (valor: string) => {
      setSearchState(valor)
      setPage(1)
    },
    setEstado: (valor: EstadoFiltro) => {
      setEstadoState(valor)
      setPage(1)
    },
    setGrupo: (valor: string) => {
      setGrupoState(valor)
      setPage(1)
    },
    /** Clic en un encabezado: la misma columna invierte el sentido; otra columna ordena ascendente. */
    ordenarPor: (campo: string) => {
      setOrden((actual) =>
        actual.campo === campo
          ? { campo, sentido: actual.sentido === 'asc' ? 'desc' : 'asc' }
          : { campo, sentido: 'asc' },
      )
      setPage(1)
    },
    setPage,
  }
}
