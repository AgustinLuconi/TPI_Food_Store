import { RouterProvider } from 'react-router'
import { useSessionBootstrap } from '@/features/auth/hooks/useAuth'
import { router } from '@/routes/AppRouter'

export default function App() {
  useSessionBootstrap() // reconstruye la sesión con GET /auth/me al cargar
  return <RouterProvider router={router} />
}
