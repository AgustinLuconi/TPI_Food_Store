import { useState } from 'react'
import { getErrorMessage, toApiError } from '@/shared/api/errors'
import { DataTable, type Column } from '@/shared/components/DataTable'
import { formatearFecha } from '@/shared/lib/formato'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Checkbox } from '@/shared/ui/Checkbox'
import { Input } from '@/shared/ui/Input'
import { useUiStore } from '@/store/uiStore'
import {
  useCrearDiaBloqueado,
  useDiasBloqueados,
  useEliminarDiaBloqueado,
} from '../hooks/useConfiguracion'
import { aHora } from '../lib/horarios'
import type { DiaBloqueado } from '../types'

interface Props {
  onSaved: (mensaje: string) => void
  onFailed: (mensaje: string) => void
}

export function DiasBloqueadosPanel({ onSaved, onFailed }: Props) {
  const { data, isLoading, isError, error } = useDiasBloqueados()
  const eliminar = useEliminarDiaBloqueado()
  const openConfirm = useUiStore((s) => s.openConfirm)

  const columnas: Column<DiaBloqueado>[] = [
    {
      key: 'fecha',
      header: 'Fecha',
      render: (d) => <span className="font-semibold">{formatearFecha(d.fecha)}</span>,
    },
    { key: 'motivo', header: 'Motivo', render: (d) => d.motivo ?? '—' },
    {
      key: 'alcance',
      header: 'Cierre',
      render: (d) =>
        d.todo_el_dia
          ? 'Todo el día'
          : `De ${aHora(d.hora_desde ?? '')} a ${aHora(d.hora_hasta ?? '')}`,
    },
  ]

  function pedirEliminar(d: DiaBloqueado) {
    openConfirm({
      titulo: 'Eliminar cierre',
      mensaje: `¿Eliminar el cierre del ${formatearFecha(d.fecha)}? El local volverá a abrir ese día según sus horarios.`,
      confirmLabel: 'Eliminar',
      tono: 'danger',
      onConfirm: async () => {
        try {
          await eliminar.mutateAsync(d.id)
          onSaved(`Se eliminó el cierre del ${formatearFecha(d.fecha)}.`)
        } catch (e) {
          onFailed(getErrorMessage(e))
        }
      },
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <NuevoCierre onSaved={onSaved} />
      <Card className="overflow-hidden p-0">
        {isError ? (
          <p role="alert" className="p-6 text-sm text-danger-700">
            {getErrorMessage(error)}
          </p>
        ) : (
          <DataTable
            columns={columnas}
            rows={data ?? []}
            rowKey={(d) => d.id}
            isLoading={isLoading}
            emptyTitle="No hay cierres cargados"
            emptyDescription="Cargá los feriados y cierres especiales para que el local no reciba pedidos esos días."
            actions={(d) => (
              <Button size="sm" variant="danger" onClick={() => pedirEliminar(d)}>
                Eliminar
              </Button>
            )}
          />
        )}
      </Card>
    </div>
  )
}

function NuevoCierre({ onSaved }: { onSaved: (mensaje: string) => void }) {
  const [fecha, setFecha] = useState('')
  const [motivo, setMotivo] = useState('')
  const [todoElDia, setTodoElDia] = useState(true)
  const [desde, setDesde] = useState('')
  const [hasta, setHasta] = useState('')
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const crear = useCrearDiaBloqueado()

  function enviar() {
    if (!fecha) return setErrorLocal('Elegí la fecha del cierre.')
    if (!todoElDia && (!desde || !hasta))
      return setErrorLocal('Un cierre parcial necesita hora de inicio y de fin.')
    if (!todoElDia && hasta <= desde)
      return setErrorLocal('La hora de fin debe ser posterior a la de inicio.')
    setErrorLocal(null)
    crear.mutate(
      {
        fecha,
        motivo: motivo.trim() || null,
        todo_el_dia: todoElDia,
        hora_desde: todoElDia ? null : desde,
        hora_hasta: todoElDia ? null : hasta,
      },
      {
        onSuccess: () => {
          onSaved(`Se cargó el cierre del ${formatearFecha(`${fecha}T12:00:00`)}.`)
          setFecha('')
          setMotivo('')
        },
      },
    )
  }
  const errorServidor = crear.error ? toApiError(crear.error).message : null

  return (
    <Card>
      <form
        noValidate
        aria-label="Agregar cierre"
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="grid gap-4 sm:grid-cols-2"
      >
        <h2 className="font-bold text-navy-900 sm:col-span-2">Agregar cierre</h2>
        <Input
          label="Fecha"
          required
          type="date"
          value={fecha}
          onChange={(e) => setFecha(e.target.value)}
        />
        <Input
          label="Motivo"
          maxLength={120}
          value={motivo}
          onChange={(e) => setMotivo(e.target.value)}
        />
        <div className="sm:col-span-2">
          <Checkbox
            label="Cierra todo el día"
            checked={todoElDia}
            onChange={(e) => setTodoElDia(e.target.checked)}
          />
        </div>
        {!todoElDia && (
          <>
            <Input
              label="Desde"
              type="time"
              value={desde}
              onChange={(e) => setDesde(e.target.value)}
            />
            <Input
              label="Hasta"
              type="time"
              value={hasta}
              onChange={(e) => setHasta(e.target.value)}
            />
          </>
        )}
        {(errorLocal ?? errorServidor) && (
          <p
            role="alert"
            className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700 sm:col-span-2"
          >
            {errorLocal ?? errorServidor}
          </p>
        )}
        <div className="sm:col-span-2">
          <Button type="submit" loading={crear.isPending}>
            Agregar cierre
          </Button>
        </div>
      </form>
    </Card>
  )
}
