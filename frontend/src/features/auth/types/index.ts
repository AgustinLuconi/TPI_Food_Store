export interface RegisterPayload {
  nombre: string
  apellido: string
  email: string
  telefono?: string
  password: string
}

export interface ChangePasswordPayload {
  password_actual: string
  password_nueva: string
}
