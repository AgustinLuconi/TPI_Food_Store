import { lazy } from 'react'
import { createBrowserRouter } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { ROLES_PERSONAL } from '@/shared/types/auth'
import { ProtectedRoute } from './ProtectedRoute'
import { RoleBasedRoute } from './RoleBasedRoute'
import { AdminShell, PublicShell, RootShell } from './Shells'

// Páginas cargadas con lazy (+ Suspense en RootShell): cada una es un chunk aparte.
const GestionDePedidosPage = lazy(() => import('@/features/pedidos/pages/GestionDePedidosPage'))
const GestionDePedidoPage = lazy(() => import('@/features/pedidos/pages/GestionDePedidoPage'))
const CheckoutPage = lazy(() => import('@/pages/CheckoutPage'))
const DireccionesPage = lazy(() => import('@/features/direcciones/pages/DireccionesPage'))
const MisPedidosPage = lazy(() => import('@/features/pedidos/pages/MisPedidosPage'))
const PedidoDetallePage = lazy(() => import('@/features/pedidos/pages/PedidoDetallePage'))
const PagarPedidoPage = lazy(() => import('@/features/pedidos/pages/PagarPedidoPage'))
const CatalogoPage = lazy(() => import('@/features/catalogo/pages/CatalogoPage'))
const ProductoDetallePage = lazy(() => import('@/features/catalogo/pages/ProductoDetallePage'))
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
const ProductosPage = lazy(() => import('@/features/catalogo/pages/ProductosPage'))
const IngredientesPage = lazy(() => import('@/features/catalogo/pages/IngredientesPage'))
const InventarioPage = lazy(() => import('@/features/inventario/pages/InventarioPage'))
const ProduccionPage = lazy(() => import('@/features/inventario/pages/ProduccionPage'))
const ConfiguracionPage = lazy(() => import('@/features/configuracion/pages/ConfiguracionPage'))

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
          { path: RUTAS.inicio, element: <CatalogoPage /> },
          { path: '/producto/:id', element: <ProductoDetallePage /> },
          { path: RUTAS.exito, element: <Success /> },
          { path: RUTAS.error, element: <ErrorPage /> },
          { path: RUTAS.noAutorizado, element: <Unauthorized /> },
          {
            element: <ProtectedRoute />,
            children: [
              { path: RUTAS.perfil, element: <ProfilePage /> },
              {
                // Pedir es del cliente: el personal gestiona pedidos desde el panel.
                element: <RoleBasedRoute allowedRoles={['CLIENT']} />,
                children: [
                  { path: RUTAS.checkout, element: <CheckoutPage /> },
                  { path: RUTAS.direcciones, element: <DireccionesPage /> },
                  { path: RUTAS.pedidos, element: <MisPedidosPage /> },
                  { path: '/pedidos/:id', element: <PedidoDetallePage /> },
                  { path: '/pedidos/:id/pagar', element: <PagarPedidoPage /> },
                ],
              },
            ],
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
                      { path: RUTAS.adminConfiguracion, element: <ConfiguracionPage /> },
                    ],
                  },
                  {
                    element: <RoleBasedRoute allowedRoles={['ADMIN', 'PEDIDOS']} />,
                    children: [
                      { path: RUTAS.adminPedidos, element: <GestionDePedidosPage /> },
                      { path: '/admin/pedidos/:id', element: <GestionDePedidoPage /> },
                    ],
                  },
                  {
                    // Catálogo (lectura y disponibilidad), inventario y producción: ADMIN y STOCK.
                    element: <RoleBasedRoute allowedRoles={['ADMIN', 'STOCK']} />,
                    children: [
                      { path: RUTAS.adminProductos, element: <ProductosPage /> },
                      { path: RUTAS.adminIngredientes, element: <IngredientesPage /> },
                      { path: RUTAS.adminInventario, element: <InventarioPage /> },
                      { path: RUTAS.adminProduccion, element: <ProduccionPage /> },
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
