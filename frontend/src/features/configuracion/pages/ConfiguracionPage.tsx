import { useState } from 'react'
import { useResultado } from '@/shared/hooks/useResultado'
import { RUTAS } from '@/shared/lib/rutas'
import { Tabs } from '@/shared/ui/Tabs'
import { DiasBloqueadosPanel } from '../components/DiasBloqueadosPanel'
import { HorariosPanel } from '../components/HorariosPanel'
import { LocalPanel } from '../components/LocalPanel'
import { ZonasPanel } from '../components/ZonasPanel'

const VOLVER = { volverA: RUTAS.adminConfiguracion, volverLabel: 'Volver a configuración' }

export default function ConfiguracionPage() {
  const [pestana, setPestana] = useState('local')
  const { exito, fallo } = useResultado()

  return (
    <div className="flex flex-col gap-4 p-4 sm:p-8">
      <h1 className="text-2xl font-bold text-navy-900">Configuración</h1>
      <Tabs
        etiqueta="Secciones de la configuración"
        activa={pestana}
        onChange={setPestana}
        pestanas={[
          {
            id: 'local',
            label: 'Local',
            contenido: (
              <LocalPanel
                onSaved={() =>
                  exito({
                    titulo: 'Local actualizado',
                    mensaje: 'Los datos del local se guardaron correctamente.',
                    ...VOLVER,
                  })
                }
              />
            ),
          },
          {
            id: 'horarios',
            label: 'Horarios',
            contenido: (
              <HorariosPanel
                onSaved={() =>
                  exito({
                    titulo: 'Horarios guardados',
                    mensaje: 'Las franjas operativas se guardaron correctamente.',
                    ...VOLVER,
                  })
                }
              />
            ),
          },
          {
            id: 'bloqueados',
            label: 'Días bloqueados',
            contenido: (
              <DiasBloqueadosPanel
                onSaved={(mensaje) => exito({ titulo: 'Cierres actualizados', mensaje, ...VOLVER })}
                onFailed={(mensaje) =>
                  fallo({ titulo: 'No se pudo completar la acción', mensaje, ...VOLVER })
                }
              />
            ),
          },
          {
            id: 'zonas',
            label: 'Zonas de cobertura',
            contenido: (
              <ZonasPanel
                onSaved={(titulo, mensaje) => exito({ titulo, mensaje, ...VOLVER })}
                onFailed={(titulo, mensaje) => fallo({ titulo, mensaje, ...VOLVER })}
              />
            ),
          },
        ]}
      />
    </div>
  )
}
