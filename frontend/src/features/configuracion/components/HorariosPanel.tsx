import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { Button } from '@/shared/ui/Button'
import { Card } from '@/shared/ui/Card'
import { Checkbox } from '@/shared/ui/Checkbox'
import { Input } from '@/shared/ui/Input'
import { Spinner } from '@/shared/ui/Spinner'
import { useGuardarHorarios, useHorarios } from '../hooks/useConfiguracion'
import { agruparPorDia, aItems, nuevaFranja, validarHorarios, type Franja } from '../lib/horarios'
import { DIAS, type Horario } from '../types'

export function HorariosPanel({ onSaved }: { onSaved: () => void }) {
  const { data, isLoading, isError } = useHorarios()
  if (isLoading) return <Spinner />
  if (isError || !data)
    return (
      <p role="alert" className="text-sm text-danger-700">
        No se pudieron cargar los horarios.
      </p>
    )
  return <Editor horarios={data} onSaved={onSaved} />
}

function Editor({ horarios, onSaved }: { horarios: Horario[]; onSaved: () => void }) {
  const [dias, setDias] = useState<Franja[][]>(() => agruparPorDia(horarios))
  const [errorLocal, setErrorLocal] = useState<string | null>(null)
  const guardar = useGuardarHorarios()

  function cambiar(dia: number, clave: number, cambios: Partial<Franja>) {
    setDias((actual) =>
      actual.map((fs, d) =>
        d === dia ? fs.map((f) => (f.clave === clave ? { ...f, ...cambios } : f)) : fs,
      ),
    )
  }

  function enviar() {
    const problema = validarHorarios(dias, DIAS)
    setErrorLocal(problema)
    if (!problema) guardar.mutate(aItems(dias), { onSuccess: onSaved })
  }
  const errorServidor = guardar.error ? toApiError(guardar.error).message : null

  return (
    <Card>
      <form
        noValidate
        aria-label="Horarios operativos"
        onSubmit={(e) => {
          e.preventDefault()
          enviar()
        }}
        className="flex flex-col gap-4"
      >
        <p className="text-sm text-navy-500">
          Cada día admite varias franjas (por ejemplo, almuerzo y cena). El cierre es exclusivo y la
          franja no cruza la medianoche.
        </p>
        {DIAS.map((nombre, dia) => (
          <fieldset key={nombre} className="rounded-lg border border-surface-border p-3">
            <legend className="px-1 text-sm font-bold text-navy-900">{nombre}</legend>
            {dias[dia].length === 0 && (
              <p className="text-sm text-navy-500">Cerrado todo el día.</p>
            )}
            <div className="flex flex-col gap-3">
              {dias[dia].map((f) => (
                <div key={f.clave} className="flex flex-wrap items-end gap-3">
                  <Input
                    label={`${nombre}: apertura`}
                    type="time"
                    value={f.apertura}
                    onChange={(e) => cambiar(dia, f.clave, { apertura: e.target.value })}
                  />
                  <Input
                    label={`${nombre}: cierre`}
                    type="time"
                    value={f.cierre}
                    onChange={(e) => cambiar(dia, f.clave, { cierre: e.target.value })}
                  />
                  <div className="pb-2">
                    <Checkbox
                      label="Activa"
                      checked={f.activo}
                      onChange={(e) => cambiar(dia, f.clave, { activo: e.target.checked })}
                    />
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      setDias((a) =>
                        a.map((fs, d) => (d === dia ? fs.filter((x) => x.clave !== f.clave) : fs)),
                      )
                    }
                  >
                    Quitar
                  </Button>
                </div>
              ))}
            </div>
            <div className="mt-3">
              <Button
                size="sm"
                variant="secondary"
                onClick={() =>
                  setDias((a) => a.map((fs, d) => (d === dia ? [...fs, nuevaFranja()] : fs)))
                }
              >
                + Agregar franja
              </Button>
            </div>
          </fieldset>
        ))}
        {(errorLocal ?? errorServidor) && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {errorLocal ?? errorServidor}
          </p>
        )}
        <div>
          <Button type="submit" loading={guardar.isPending}>
            Guardar horarios
          </Button>
        </div>
      </form>
    </Card>
  )
}
