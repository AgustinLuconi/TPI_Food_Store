import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatearDinero } from '@/shared/lib/formato'
import { dineroCompacto, fechaCorta } from '../lib/fechas'
import { cantidadConUnidad, etiquetaDeMerma, textoDelDetalle } from '../lib/mermas'
import type { MermaPorMotivo, PuntoDeVentas, TopProducto } from '../types'
import { ChartCard } from './Bloques'

// Paleta del sistema de diseño: navy para la estructura y naranja para lo que se destaca (sección 11.4).
const NARANJA = '#ea580c'
const NAVY = '#0f172a'
const GRIS = '#e2e8f0'

export function GraficoDeVentas({ serie, total }: { serie: PuntoDeVentas[]; total: string }) {
  const datos = serie.map((p) => ({ fecha: p.fecha, total: Number(p.total), pedidos: p.pedidos }))
  return (
    <ChartCard
      titulo="Ingresos por día"
      descripcion={`Ingresos diarios de los últimos ${serie.length} días. Total: ${formatearDinero(total)}.`}
      vacio={serie.length === 0}
      tabla={{
        columnas: ['Día', 'Pedidos', 'Ingresos'],
        filas: serie.map((p) => [p.fecha, p.pedidos, formatearDinero(p.total)]),
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={GRIS} strokeDasharray="3 3" />
          <XAxis dataKey="fecha" tickFormatter={fechaCorta} fontSize={12} minTickGap={24} />
          <YAxis tickFormatter={dineroCompacto} fontSize={12} width={64} />
          <Tooltip
            formatter={(v) => formatearDinero(Number(v))}
            labelFormatter={(l) => fechaCorta(String(l))}
          />
          <Line
            type="monotone"
            dataKey="total"
            name="Ingresos"
            stroke={NARANJA}
            strokeWidth={2.5}
            dot={datos.length <= 14}
          />
        </LineChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export function GraficoTopProductos({ productos }: { productos: TopProducto[] }) {
  const datos = productos.map((p) => ({ nombre: p.nombre, unidades: p.unidades }))
  return (
    <ChartCard
      titulo="Productos más vendidos"
      descripcion={`Los ${productos.length} productos más vendidos, por unidades.`}
      vacio={productos.length === 0}
      tabla={{
        columnas: ['Producto', 'Unidades', 'Ingresos'],
        filas: productos.map((p) => [p.nombre, p.unidades, formatearDinero(p.ingresos)]),
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 8 }}>
          <CartesianGrid stroke={GRIS} strokeDasharray="3 3" horizontal={false} />
          <XAxis type="number" allowDecimals={false} fontSize={12} />
          <YAxis
            type="category"
            dataKey="nombre"
            width={150}
            fontSize={12}
            tickFormatter={(n: string) => (n.length > 22 ? `${n.slice(0, 21)}…` : n)}
          />
          <Tooltip />
          <Bar
            dataKey="unidades"
            name="Unidades"
            fill={NARANJA}
            radius={[0, 4, 4, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export function GraficoPorEstado({
  titulo,
  datos,
  descripcion,
}: {
  titulo: string
  datos: Record<string, number>
  descripcion: string
}) {
  const filas = Object.entries(datos).map(([estado, cantidad]) => ({ estado, cantidad }))
  return (
    <ChartCard
      titulo={titulo}
      descripcion={descripcion}
      vacio={filas.length === 0}
      tabla={{ columnas: ['Estado', 'Cantidad'], filas: filas.map((f) => [f.estado, f.cantidad]) }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={filas} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={GRIS} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="estado"
            fontSize={11}
            interval={0}
            angle={-20}
            textAnchor="end"
            height={56}
          />
          <YAxis allowDecimals={false} fontSize={12} />
          <Tooltip />
          <Bar
            dataKey="cantidad"
            name="Cantidad"
            fill={NAVY}
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

export function GraficoDeMermas({ titulo, mermas }: { titulo: string; mermas: MermaPorMotivo[] }) {
  const datos = mermas.map((m) => ({ motivo: etiquetaDeMerma(m), cantidad: Number(m.cantidad) }))
  const conDetalle = mermas.some((m) => (m.detalle ?? []).length > 0)
  return (
    <ChartCard
      titulo={titulo}
      descripcion={`${titulo}: cantidad perdida por motivo.`}
      vacio={mermas.length === 0}
      detalle={conDetalle ? <DetalleDeMermas mermas={mermas} /> : undefined}
      tabla={{
        columnas: conDetalle
          ? ['Motivo', 'Cantidad', 'Movimientos', 'Insumos']
          : ['Motivo', 'Cantidad', 'Movimientos'],
        filas: mermas.map((m) => [
          etiquetaDeMerma(m),
          cantidadConUnidad(m.cantidad, m.unidad_medida),
          m.movimientos,
          ...(conDetalle ? [textoDelDetalle(m)] : []),
        ]),
      }}
    >
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid stroke={GRIS} strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="motivo"
            fontSize={11}
            interval={0}
            angle={-15}
            textAnchor="end"
            height={52}
          />
          <YAxis allowDecimals fontSize={12} />
          <Tooltip />
          <Bar
            dataKey="cantidad"
            name="Cantidad"
            fill={NARANJA}
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </ChartCard>
  )
}

/** El total de cada motivo y, debajo, cuánto aportó cada insumo (siempre visible, sin abrir la tabla). */
function DetalleDeMermas({ mermas }: { mermas: MermaPorMotivo[] }) {
  return (
    <ul aria-label="Mermas de insumos: qué aportó cada uno" className="flex flex-col gap-2 text-sm">
      {mermas.map((m) => (
        <li key={etiquetaDeMerma(m)}>
          <p className="font-semibold text-navy-900">
            {etiquetaDeMerma(m)} · {cantidadConUnidad(m.cantidad, m.unidad_medida)}
          </p>
          <ul className="ml-4 list-disc text-navy-700">
            {(m.detalle ?? []).map((d) => (
              <li key={d.ingrediente_id}>
                {d.nombre}: {cantidadConUnidad(d.cantidad, m.unidad_medida)}
              </li>
            ))}
          </ul>
        </li>
      ))}
    </ul>
  )
}
