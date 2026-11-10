import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { toApiError } from '@/shared/api/errors'
import { AuthLayout } from '@/shared/layout/AuthLayout'
import { homePorRoles, RUTAS } from '@/shared/lib/rutas'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { useAuthStore } from '@/store/authStore'
import { useLogin } from '../hooks/useAuth'

interface LocationState {
  from?: string
}

export default function LoginPage() {
  const navigate = useNavigate()
  const location = useLocation()
  const usuario = useAuthStore((s) => s.usuario)
  const login = useLogin()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const destino = (location.state as LocationState | null)?.from

  // Quien ya tiene sesión no necesita ver el login.
  if (usuario) return <Navigate to={destino ?? homePorRoles(usuario.roles)} replace />

  function enviar(e: FormEvent) {
    e.preventDefault()
    login.mutate(
      { email: email.trim(), password },
      { onSuccess: (u) => navigate(destino ?? homePorRoles(u.roles), { replace: true }) },
    )
  }

  const error = login.error ? toApiError(login.error) : null

  return (
    <AuthLayout titulo="Iniciar sesión">
      <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
        <Input
          label="Email"
          type="email"
          autoComplete="username"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <Input
          label="Contraseña"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {error.message}
          </p>
        )}
        <Button type="submit" loading={login.isPending} disabled={!email || !password}>
          Ingresar
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-navy-700">
        ¿No tenés cuenta?{' '}
        <Link to={RUTAS.registro} className="font-semibold text-accent-700 underline">
          Registrate
        </Link>
      </p>
    </AuthLayout>
  )
}
