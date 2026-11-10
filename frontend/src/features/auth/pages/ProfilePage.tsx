import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { toApiError } from '@/shared/api/errors'
import type { ResultadoState } from '@/shared/types/resultado'
import { ROL_NOMBRE } from '@/shared/types/auth'
import { homePorRoles, RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Input } from '@/shared/ui/Input'
import { useAuthStore } from '@/store/authStore'
import { useChangePassword } from '../hooks/useAuth'
import { POLITICA_PASSWORD, validarPassword } from '@/shared/lib/passwordPolicy'

export default function ProfilePage() {
  const navigate = useNavigate()
  const usuario = useAuthStore((s) => s.usuario)
  const cambio = useChangePassword()
  const [actual, setActual] = useState('')
  const [nueva, setNueva] = useState('')
  const [confirmacion, setConfirmacion] = useState('')
  const [errorLocal, setErrorLocal] = useState<{ campo: string; mensaje: string } | null>(null)

  if (!usuario) return null // ProtectedRoute garantiza la sesión; esto solo satisface a TypeScript

  function enviar(e: FormEvent) {
    e.preventDefault()
    const politica = validarPassword(nueva)
    if (politica) return setErrorLocal({ campo: 'password_nueva', mensaje: politica })
    if (nueva !== confirmacion)
      return setErrorLocal({ campo: 'confirmacion', mensaje: 'Las contraseñas no coinciden' })
    setErrorLocal(null)

    cambio.mutate(
      { password_actual: actual, password_nueva: nueva },
      {
        onSuccess: () => {
          const resultado: ResultadoState = {
            titulo: 'Contraseña actualizada',
            mensaje: 'Tu contraseña se cambió correctamente. Cerramos tus otras sesiones.',
            volverA: usuario ? homePorRoles(usuario.roles) : RUTAS.inicio,
            volverLabel: 'Volver al inicio',
          }
          navigate(RUTAS.exito, { state: resultado })
        },
      },
    )
  }

  const errorServidor = cambio.error ? toApiError(cambio.error) : null
  const mensajeDe = (campo: string) =>
    errorLocal?.campo === campo
      ? errorLocal.mensaje
      : errorServidor?.field === campo
        ? errorServidor.message
        : undefined

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-6 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Mi perfil</h1>

      <Card>
        <h2 className="mb-4 text-lg font-bold text-navy-900">Datos de la cuenta</h2>
        <dl className="grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-navy-500">Nombre</dt>
            <dd className="font-semibold">
              {usuario.nombre} {usuario.apellido}
            </dd>
          </div>
          <div>
            <dt className="text-navy-500">Email</dt>
            <dd className="font-semibold">{usuario.email}</dd>
          </div>
          <div>
            <dt className="text-navy-500">Teléfono</dt>
            <dd className="font-semibold">{usuario.telefono ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-navy-500">Roles</dt>
            <dd className="mt-1 flex flex-wrap gap-2">
              {usuario.roles.map((rol) => (
                <Badge key={rol} tone="accent">
                  {ROL_NOMBRE[rol]}
                </Badge>
              ))}
            </dd>
          </div>
        </dl>
      </Card>

      <Card>
        <h2 className="mb-4 text-lg font-bold text-navy-900">Cambiar contraseña</h2>
        <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
          <Input
            label="Contraseña actual"
            type="password"
            autoComplete="current-password"
            required
            value={actual}
            onChange={(e) => setActual(e.target.value)}
            error={mensajeDe('password_actual')}
          />
          <Input
            label="Contraseña nueva"
            type="password"
            autoComplete="new-password"
            required
            hint={POLITICA_PASSWORD}
            value={nueva}
            onChange={(e) => setNueva(e.target.value)}
            error={mensajeDe('password_nueva')}
          />
          <Input
            label="Repetir contraseña nueva"
            type="password"
            autoComplete="new-password"
            required
            value={confirmacion}
            onChange={(e) => setConfirmacion(e.target.value)}
            error={mensajeDe('confirmacion')}
          />
          {errorServidor && !errorServidor.field && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
              {errorServidor.message}
            </p>
          )}
          <Button type="submit" loading={cambio.isPending} disabled={!actual || !nueva}>
            Actualizar contraseña
          </Button>
        </form>
      </Card>
    </div>
  )
}
