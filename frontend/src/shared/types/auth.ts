export type Rol = 'ADMIN' | 'STOCK' | 'PEDIDOS' | 'CLIENT'

export const ROLES: readonly Rol[] = ['ADMIN', 'STOCK', 'PEDIDOS', 'CLIENT']

export const ROL_NOMBRE: Record<Rol, string> = {
  ADMIN: 'Administrador',
  STOCK: 'Gestor de stock',
  PEDIDOS: 'Gestor de pedidos',
  CLIENT: 'Cliente',
}

/** Usuario devuelto por la API. Nunca incluye la contraseña ni su hash. */
export interface Usuario {
  id: number
  nombre: string
  apellido: string
  email: string
  telefono: string | null
  disabled: boolean
  roles: Rol[]
  created_at: string
  deleted_at: string | null
}

/** Roles del personal: acceden al panel de administración. */
export const ROLES_PERSONAL: readonly Rol[] = ['ADMIN', 'STOCK', 'PEDIDOS']
