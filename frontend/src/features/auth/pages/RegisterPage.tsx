import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router'
import { toApiError } from '@/shared/api/errors'
import { AuthLayout } from '@/shared/layout/AuthLayout'
import { homePorRoles, RUTAS } from '@/shared/lib/rutas'
import type { ResultadoState } from '@/shared/types/resultado'
import { Button } from '@/shared/ui/Button'
import { Input } from '@/shared/ui/Input'
import { useAuthStore } from '@/store/authStore'
import { useRegister } from '../hooks/useAuth'
import { POLITICA_PASSWORD, validarPassword } from '@/shared/lib/passwordPolicy'

type Campos = 'nombre' | 'apellido' | 'email' | 'password' | 'confirmacion'
type Errores = Partial<Record<Campos, string>>

export default function RegisterPage() {
  const navigate = useNavigate()
  const usuario = useAuthStore((s) => s.usuario)
  const registro = useRegister()
  const [form, setForm] = useState({
    nombre: '',
    apellido: '',
    email: '',
    telefono: '',
    password: '',
    confirmacion: '',
  })
  const [errores, setErrores] = useState<Errores>({})

  if (usuario) return <Navigate to={homePorRoles(usuario.roles)} replace />

  const cambiar = (campo: keyof typeof form) => (e: { target: { value: string } }) =>
    setForm((f) => ({ ...f, [campo]: e.target.value }))

  function validar(): Errores {
    const e: Errores = {}
    if (!form.nombre.trim()) e.nombre = 'Ingresá tu nombre'
    if (!form.apellido.trim()) e.apellido = 'Ingresá tu apellido'
    if (!/^\S+@\S+\.\S+$/.test(form.email)) e.email = 'Ingresá un email válido'
    const pw = validarPassword(form.password)
    if (pw) e.password = pw
    if (form.confirmacion !== form.password) e.confirmacion = 'Las contraseñas no coinciden'
    return e
  }

  function enviar(ev: FormEvent) {
    ev.preventDefault()
    const e = validar()
    setErrores(e)
    if (Object.keys(e).length > 0) return

    registro.mutate(
      {
        nombre: form.nombre.trim(),
        apellido: form.apellido.trim(),
        email: form.email.trim(),
        telefono: form.telefono.trim() || undefined,
        password: form.password,
      },
      {
        onSuccess: () => {
          const resultado: ResultadoState = {
            titulo: 'Cuenta creada',
            mensaje: 'Tu cuenta se creó correctamente. Ya podés iniciar sesión.',
            volverA: RUTAS.login,
            volverLabel: 'Iniciar sesión',
          }
          navigate(RUTAS.exito, { state: resultado })
        },
      },
    )
  }

  // Los errores de campo que devuelve el servidor (p. ej. email duplicado) se muestran bajo su campo.
  const errorServidor = registro.error ? toApiError(registro.error) : null
  const campoServidor = (campo: Campos) =>
    errorServidor?.field === campo ? errorServidor.message : undefined
  const errorGeneral = errorServidor && !(errorServidor.field && errorServidor.field in form)

  return (
    <AuthLayout titulo="Crear cuenta">
      <form onSubmit={enviar} className="flex flex-col gap-4" noValidate>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input
            label="Nombre"
            required
            autoComplete="given-name"
            value={form.nombre}
            onChange={cambiar('nombre')}
            error={errores.nombre ?? campoServidor('nombre')}
          />
          <Input
            label="Apellido"
            required
            autoComplete="family-name"
            value={form.apellido}
            onChange={cambiar('apellido')}
            error={errores.apellido ?? campoServidor('apellido')}
          />
        </div>
        <Input
          label="Email"
          type="email"
          required
          autoComplete="email"
          value={form.email}
          onChange={cambiar('email')}
          error={errores.email ?? campoServidor('email')}
        />
        <Input
          label="Teléfono"
          type="tel"
          autoComplete="tel"
          value={form.telefono}
          onChange={cambiar('telefono')}
        />
        <Input
          label="Contraseña"
          type="password"
          required
          autoComplete="new-password"
          hint={POLITICA_PASSWORD}
          value={form.password}
          onChange={cambiar('password')}
          error={errores.password ?? campoServidor('password')}
        />
        <Input
          label="Repetir contraseña"
          type="password"
          required
          autoComplete="new-password"
          value={form.confirmacion}
          onChange={cambiar('confirmacion')}
          error={errores.confirmacion}
        />
        {errorGeneral && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {errorServidor.message}
          </p>
        )}
        <Button type="submit" loading={registro.isPending}>
          Crear cuenta
        </Button>
      </form>
      <p className="mt-6 text-center text-sm text-navy-700">
        ¿Ya tenés cuenta?{' '}
        <Link to={RUTAS.login} className="font-semibold text-accent-700 underline">
          Iniciá sesión
        </Link>
      </p>
    </AuthLayout>
  )
}
