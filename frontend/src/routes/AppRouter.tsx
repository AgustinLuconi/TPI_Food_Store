import { lazy } from 'react'
import { createBrowserRouter } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { ROLES_PERSONAL } from '@/shared/types/auth'
import { ProtectedRoute } from './ProtectedRoute'
import { RoleBasedRoute } from './RoleBasedRoute'
import { AdminShell, PublicShell, RootShell } from './Shells'

// Páginas cargadas con lazy (+ Suspense en RootShell): cada una es un chunk aparte.
const Home = lazy(() => import('@/pages/Home'))
const AdminHome = lazy(() => import('@/pages/AdminHome'))
const Success = lazy(() => import('@/pages/Success'))
const ErrorPage = lazy(() => import('@/pages/Error'))
const Unauthorized = lazy(() => import('@/pages/Unauthorized'))
const NotFound = lazy(() => import('@/pages/NotFound'))
const LoginPage = lazy(() => import('@/features/auth/pages/LoginPage'))
const RegisterPage = lazy(() => import('@/features/auth/pages/RegisterPage'))
const ProfilePage = lazy(() => import('@/features/auth/pages/ProfilePage'))
const CategoriasPage = lazy(() => import('@/features/maestros/pages/CategoriasPage'))
const UsuariosPage = lazy(() => import('@/features/maestros/pages/UsuariosPage'))

export const router = createBrowserRouter([
  {
    element: <RootShell />,
    children: [
      { path: RUTAS.login, element: <LoginPage /> },
      { path: RUTAS.registro, element: <RegisterPage /> },
      {
        // Sitio público con header y footer.
        element: <PublicShell />,
        children: [
          { path: RUTAS.inicio, element: <Home /> },
          { path: RUTAS.exito, element: <Success /> },
          { path: RUTAS.error, element: <ErrorPage /> },
          { path: RUTAS.noAutorizado, element: <Unauthorized /> },
          {
            element: <ProtectedRoute />,
            children: [{ path: RUTAS.perfil, element: <ProfilePage /> }],
          },
          { path: '*', element: <NotFound /> },
        ],
      },
      {
        // Panel de administración: requiere sesión y rol de personal; cada pantalla, su rol.
        element: <ProtectedRoute />,
        children: [
          {
            element: <RoleBasedRoute allowedRoles={ROLES_PERSONAL} />,
            children: [
              {
                element: <AdminShell />,
                children: [
                  { path: RUTAS.admin, element: <AdminHome /> },
                  {
                    element: <RoleBasedRoute allowedRoles={['ADMIN']} />,
                    children: [
                      { path: RUTAS.adminCategorias, element: <CategoriasPage /> },
                      { path: RUTAS.adminUsuarios, element: <UsuariosPage /> },
                    ],
                  },
                ],
              },
            ],
          },
        ],
      },
    ],
  },
])
