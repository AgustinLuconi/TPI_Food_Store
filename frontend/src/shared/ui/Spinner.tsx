export function Spinner({ label = 'Cargando…' }: { label?: string }) {
  return (
    <div role="status" className="flex flex-col items-center justify-center gap-3 p-10">
      <span
        aria-hidden="true"
        className="size-8 animate-spin rounded-full border-4 border-surface-border border-t-accent-600"
      />
      <span className="text-sm text-navy-500">{label}</span>
    </div>
  )
}
