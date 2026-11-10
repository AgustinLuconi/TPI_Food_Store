import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import App from '@/App'
import { limpiarSesionLocal } from '@/features/auth/hooks/useAuth'
import { router } from '@/routes/AppRouter'
import { setSessionExpiredHandler } from '@/shared/api/axiosInstance'
import { queryClient } from '@/shared/api/queryClient'
import { RUTAS } from '@/shared/lib/rutas'
import '@/styles/global.css'

// Si Axios no logra renovar la sesión (refresh fallido tras un 401): limpiar todo y volver al login.
setSessionExpiredHandler(() => {
  limpiarSesionLocal()
  const actual = router.state.location.pathname
  if (actual !== RUTAS.login && actual !== RUTAS.registro) {
    void router.navigate(RUTAS.login, { replace: true, state: { from: actual } })
  }
})

const root = document.getElementById('root')
if (!root) throw new Error('No se encontró el elemento #root')

createRoot(root).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </StrictMode>,
)
