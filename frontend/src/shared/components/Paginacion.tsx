import { Button } from '@/shared/ui/Button'

interface PaginacionProps {
  page: number
  pages: number
  total: number
  onPageChange: (page: number) => void
}

export function Paginacion({ page, pages, total, onPageChange }: PaginacionProps) {
  return (
    <nav
      aria-label="Paginación"
      className="flex items-center justify-between gap-3 border-t border-surface-border px-4 py-3"
    >
      <p className="text-sm text-navy-500">
        {total} {total === 1 ? 'resultado' : 'resultados'}
        {pages > 0 && ` · Página ${page} de ${pages}`}
      </p>
      <div className="flex gap-2">
        <Button
          variant="secondary"
          size="sm"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Anterior
        </Button>
        <Button
          variant="secondary"
          size="sm"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Siguiente
        </Button>
      </div>
    </nav>
  )
}
