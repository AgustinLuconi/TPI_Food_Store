/** "2026-12-31" → instante ISO al final de ese día (hora local): el lote vale durante todo su último día. */
export function finDelDiaIso(fecha: string): string {
  return new Date(`${fecha}T23:59:59`).toISOString()
}

/** Hoy como "YYYY-MM-DD" en hora local (mínimo permitido para un vencimiento). */
export function hoyIso(): string {
  const d = new Date()
  const dos = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${dos(d.getMonth() + 1)}-${dos(d.getDate())}`
}
