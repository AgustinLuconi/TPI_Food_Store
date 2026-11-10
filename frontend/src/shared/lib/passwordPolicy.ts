/**
 * Espejo de la política del backend (sección 5.2): mínimo 12 caracteres, con al menos una mayúscula,
 * un dígito y un carácter especial. Es solo una ayuda de UX: la validación real es la del servidor.
 */
export function validarPassword(password: string): string | null {
  if (password.length < 12) return 'Debe tener al menos 12 caracteres'
  if (!/[A-Z]/.test(password)) return 'Debe incluir al menos una mayúscula'
  if (!/\d/.test(password)) return 'Debe incluir al menos un dígito'
  if (!/[^A-Za-z0-9]/.test(password)) return 'Debe incluir al menos un carácter especial'
  return null
}

export const POLITICA_PASSWORD =
  'Mínimo 12 caracteres, con una mayúscula, un dígito y un carácter especial.'
