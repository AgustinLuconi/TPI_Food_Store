import { useState } from 'react'
import { useDebounce } from '@/shared/hooks/useDebounce'
import type { EstadoFiltro } from '@/shared/types/common'
import type { ListParams } from '../types'

const TAMANO_PAGINA = 10

/**
 * Estado de filtros compartido por todas las pantallas de maestros (sección 11.5):
 * búsqueda con debounce, agrupación, estado (Activos por defecto) y página.
 * Cualquier cambio de filtro vuelve a la primera página.
 */
export function useMaestroFilters() {
  const [search, setSearchState] = useState('')
  const [estado, setEstadoState] = useState<EstadoFiltro>('activos')
  const [rol, setRolState] = useState('')
  const [page, setPage] = useState(1)
  const debouncedSearch = useDebounce(search, 400)

  const params: ListParams = {
    search: debouncedSearch.trim(),
    estado,
    page,
    size: TAMANO_PAGINA,
    rol: rol || undefined,
  }

  return {
    params,
    search,
    estado,
    rol,
    page,
    setSearch: (valor: string) => {
      setSearchState(valor)
      setPage(1)
    },
    setEstado: (valor: EstadoFiltro) => {
      setEstadoState(valor)
      setPage(1)
    },
    setRol: (valor: string) => {
      setRolState(valor)
      setPage(1)
    },
    setPage,
  }
}
