import { useEffect, useState } from 'react'

/** Devuelve `value` recién después de `delay` ms sin cambios (búsquedas: 300 a 500 ms). */
export function useDebounce<T>(value: T, delay = 400): T {
  const [debounced, setDebounced] = useState(value)

  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay)
    return () => clearTimeout(timer)
  }, [value, delay])

  return debounced
}
