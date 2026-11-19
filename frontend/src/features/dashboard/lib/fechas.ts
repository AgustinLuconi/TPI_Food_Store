/** "2026-11-17" menos 6 días → "2026-11-11". Aritmética de calendario pura (sin zona horaria del navegador). */
export function restarDias(fecha: string, dias: number): string {
  const [a, m, d] = fecha.split('-').map(Number)
  const resultado = new Date(Date.UTC(a, m - 1, d - dias))
  return resultado.toISOString().slice(0, 10)
}

/** "2026-11-17" → "17/11" para el eje de un gráfico. */
export function fechaCorta(fecha: string): string {
  const [, m, d] = fecha.split('-')
  return `${d}/${m}`
}

/** Un monto grande en el eje: 1.250.000 → "$ 1,3 M". */
export function dineroCompacto(valor: number): string {
  return new Intl.NumberFormat('es-AR', {
    style: 'currency',
    currency: 'ARS',
    notation: 'compact',
    maximumFractionDigits: 1,
  })
    .format(valor)
    .replace(/\s/g, ' ')
}
