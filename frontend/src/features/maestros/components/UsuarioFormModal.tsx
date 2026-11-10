import { useState } from 'react'
import { POLITICA_PASSWORD, validarPassword } from '@/shared/lib/passwordPolicy'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { ROL_NOMBRE, ROLES, type Rol, type Usuario } from '@/shared/types/auth'
import { Input } from '@/shared/ui/Input'
import { useGuardarUsuario } from '../hooks/useUsuarios'

interface Props {
  /** null = alta; con valor = edición. */
  usuario: Usuario | null
  onClose: () => void
  onSaved: (guardado: Usuario, modo: 'create' | 'edit') => void
}

export function UsuarioFormModal({ usuario, onClose, onSaved }: Props) {
  const mode = usuario ? 'edit' : 'create'
  const [nombre, setNombre] = useState(usuario?.nombre ?? '')
  const [apellido, setApellido] = useState(usuario?.apellido ?? '')
  const [email, setEmail] = useState(usuario?.email ?? '')
  const [telefono, setTelefono] = useState(usuario?.telefono ?? '')
  const [password, setPassword] = useState('')
  const [roles, setRoles] = useState<Rol[]>(usuario?.roles ?? ['CLIENT'])
  const [errores, setErrores] = useState<Record<string, string>>({})

  const guardar = useGuardarUsuario()

  function alternarRol(rol: Rol) {
    setRoles((actuales) =>
      actuales.includes(rol) ? actuales.filter((r) => r !== rol) : [...actuales, rol],
    )
  }

  function validar(): Record<string, string> {
    const e: Record<string, string> = {}
    if (!nombre.trim()) e.nombre = 'Ingresá un nombre'
    if (!apellido.trim()) e.apellido = 'Ingresá un apellido'
    if (!/^\S+@\S+\.\S+$/.test(email)) e.email = 'Ingresá un email válido'
    if (roles.length === 0) e.roles = 'Elegí al menos un rol'
    if (mode === 'create') {
      const pw = validarPassword(password)
      if (pw) e.password = pw
    }
    return e
  }

  function enviar() {
    const e = validar()
    setErrores(e)
    if (Object.keys(e).length > 0) return

    guardar.mutate(
      {
        usuario: usuario ?? undefined,
        datos: {
          nombre: nombre.trim(),
          apellido: apellido.trim(),
          email: email.trim(),
          telefono: telefono.trim() || null,
        },
        roles,
        password: mode === 'create' ? password : undefined,
      },
      { onSuccess: (guardado) => onSaved(guardado, mode) },
    )
  }

  const error = guardar.error ? toApiError(guardar.error) : null
  const mensajeDe = (campo: string) =>
    errores[campo] ?? (error?.field === campo ? error.message : undefined)

  return (
    <EntityFormModal
      open
      mode={mode}
      entityName="usuario"
      onClose={onClose}
      onSubmit={enviar}
      isSubmitting={guardar.isPending}
      error={error && !error.field ? error.message : null}
    >
      <div className="grid gap-4 sm:grid-cols-2">
        <Input
          label="Nombre"
          required
          value={nombre}
          onChange={(e) => setNombre(e.target.value)}
          error={mensajeDe('nombre')}
        />
        <Input
          label="Apellido"
          required
          value={apellido}
          onChange={(e) => setApellido(e.target.value)}
          error={mensajeDe('apellido')}
        />
      </div>
      <Input
        label="Email"
        type="email"
        required
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        error={mensajeDe('email')}
      />
      <Input
        label="Teléfono"
        type="tel"
        value={telefono}
        onChange={(e) => setTelefono(e.target.value)}
      />
      {mode === 'create' && (
        <Input
          label="Contraseña inicial"
          type="password"
          required
          autoComplete="new-password"
          hint={POLITICA_PASSWORD}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          error={mensajeDe('password')}
        />
      )}
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-semibold text-navy-900">Roles</legend>
        {ROLES.map((rol) => (
          <label key={rol} className="flex items-center gap-2 text-sm text-navy-900">
            <input
              type="checkbox"
              checked={roles.includes(rol)}
              onChange={() => alternarRol(rol)}
              className="size-4 accent-accent-600"
            />
            {ROL_NOMBRE[rol]}
          </label>
        ))}
        {mensajeDe('roles') && (
          <p role="alert" className="text-sm text-danger-700">
            {mensajeDe('roles')}
          </p>
        )}
      </fieldset>
    </EntityFormModal>
  )
}
