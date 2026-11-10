import { useState } from 'react'
import { getErrorMessage } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { FilterBar } from '@/shared/components/FilterBar'
import { Paginacion } from '@/shared/components/Paginacion'
import { useResultado } from '@/shared/hooks/useResultado'
import { RUTAS } from '@/shared/lib/rutas'
import { ROL_NOMBRE, ROLES, type Usuario } from '@/shared/types/auth'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import { UsuarioFormModal } from '../components/UsuarioFormModal'
import { useMaestroFilters } from '../hooks/useMaestroFilters'
import {
  useAnularUsuario,
  useBloquearUsuario,
  useReactivarUsuario,
  useUsuarios,
} from '../hooks/useUsuarios'

const VOLVER = { volverA: RUTAS.adminUsuarios, volverLabel: 'Volver a usuarios' }

const OPCIONES_ROL = [
  { value: '', label: 'Todos los roles' },
  ...ROLES.map((r) => ({ value: r, label: ROL_NOMBRE[r] })),
]

export default function UsuariosPage() {
  const filtros = useMaestroFilters()
  const { data, isLoading, isError, error } = useUsuarios(filtros.params)
  const [modal, setModal] = useState<{ usuario: Usuario | null; clave: number } | null>(null)

  const anular = useAnularUsuario()
  const bloquear = useBloquearUsuario()
  const reactivar = useReactivarUsuario()
  const openConfirm = useUiStore((s) => s.openConfirm)
  const yo = useAuthStore((s) => s.usuario)
  const esAdmin = useAuthStore((s) => s.hasRole('ADMIN'))
  const { exito, fallo } = useResultado()

  const columnas: Column<Usuario>[] = [
    {
      key: 'nombre',
      header: 'Nombre',
      render: (u) => (
        <span className="font-semibold">
          {u.apellido}, {u.nombre}
        </span>
      ),
    },
    { key: 'email', header: 'Email', render: (u) => u.email },
    {
      key: 'roles',
      header: 'Roles',
      render: (u) => (
        <div className="flex flex-wrap gap-1">
          {u.roles.map((r) => (
            <Badge key={r} tone="accent">
              {ROL_NOMBRE[r]}
            </Badge>
          ))}
        </div>
      ),
    },
    {
      key: 'estado',
      header: 'Cuenta',
      render: (u) =>
        u.disabled ? (
          <Badge tone="danger">Bloqueada</Badge>
        ) : (
          <Badge tone="success">Habilitada</Badge>
        ),
    },
  ]

  async function ejecutar(accion: () => Promise<unknown>, ok: string, titulo: string) {
    try {
      await accion()
      exito({ titulo, mensaje: ok, ...VOLVER })
    } catch (e) {
      fallo({ titulo: 'No se pudo completar la acción', mensaje: getErrorMessage(e), ...VOLVER })
    }
  }

  function pedirAnulacion(u: Usuario) {
    openConfirm({
      titulo: 'Anular usuario',
      mensaje: `¿Anular a ${u.nombre} ${u.apellido}? No podrá iniciar sesión. Podés reactivarlo después.`,
      confirmLabel: 'Anular',
      tono: 'danger',
      onConfirm: () =>
        ejecutar(
          () => anular.mutateAsync(u.id),
          `${u.email} se anuló correctamente.`,
          'Usuario anulado',
        ),
    })
  }

  function pedirBloqueo(u: Usuario) {
    const bloquea = !u.disabled
    openConfirm({
      titulo: bloquea ? 'Bloquear usuario' : 'Desbloquear usuario',
      mensaje: bloquea
        ? `¿Bloquear a ${u.nombre} ${u.apellido}? No podrá iniciar sesión hasta que lo desbloquees.`
        : `¿Desbloquear a ${u.nombre} ${u.apellido}?`,
      confirmLabel: bloquea ? 'Bloquear' : 'Desbloquear',
      tono: bloquea ? 'danger' : 'primary',
      onConfirm: () =>
        ejecutar(
          () => bloquear.mutateAsync({ id: u.id, disabled: bloquea }),
          `${u.email} quedó ${bloquea ? 'bloqueado' : 'desbloqueado'}.`,
          bloquea ? 'Usuario bloqueado' : 'Usuario desbloqueado',
        ),
    })
  }

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Usuarios</h1>
      <Card className="overflow-hidden p-0">
        <FilterBar
          search={filtros.search}
          onSearchChange={filtros.setSearch}
          searchPlaceholder="Buscar por nombre o email…"
          group={{
            label: 'Rol',
            value: filtros.rol,
            options: OPCIONES_ROL,
            onChange: filtros.setRol,
          }}
          estado={filtros.estado}
          onEstadoChange={filtros.setEstado}
          action={
            esAdmin && (
              <Button onClick={() => setModal({ usuario: null, clave: Date.now() })}>
                + Agregar
              </Button>
            )
          }
        />
        {isError ? (
          <p role="alert" className="p-6 text-sm text-danger-700">
            {getErrorMessage(error)}
          </p>
        ) : (
          <DataTable
            columns={columnas}
            rows={data?.items ?? []}
            rowKey={(u) => u.id}
            isLoading={isLoading}
            isInactive={(u) => u.deleted_at !== null}
            emptyTitle="No hay usuarios"
            emptyDescription="Probá con otros filtros."
            actions={
              esAdmin
                ? (u) =>
                    u.deleted_at ? (
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() =>
                          ejecutar(
                            () => reactivar.mutateAsync(u.id),
                            `${u.email} volvió a estar activo.`,
                            'Usuario reactivado',
                          )
                        }
                      >
                        Reactivar
                      </Button>
                    ) : (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={() => setModal({ usuario: u, clave: Date.now() })}
                        >
                          Modificar
                        </Button>
                        {/* No se ofrece bloquear ni anular la propia cuenta (el backend también lo rechaza). */}
                        {u.id !== yo?.id && (
                          <>
                            <Button size="sm" variant="secondary" onClick={() => pedirBloqueo(u)}>
                              {u.disabled ? 'Desbloquear' : 'Bloquear'}
                            </Button>
                            <Button size="sm" variant="danger" onClick={() => pedirAnulacion(u)}>
                              Anular
                            </Button>
                          </>
                        )}
                      </>
                    )
                : undefined
            }
          />
        )}
        {data && (
          <Paginacion
            page={data.page}
            pages={data.pages}
            total={data.total}
            onPageChange={filtros.setPage}
          />
        )}
      </Card>

      {modal && (
        <UsuarioFormModal
          key={modal.clave}
          usuario={modal.usuario}
          onClose={() => setModal(null)}
          onSaved={(guardado, modo) => {
            setModal(null)
            exito({
              titulo: modo === 'create' ? 'Usuario creado' : 'Usuario actualizado',
              mensaje: `${guardado.email} se guardó correctamente.`,
              ...VOLVER,
            })
          }}
        />
      )}
    </div>
  )
}
