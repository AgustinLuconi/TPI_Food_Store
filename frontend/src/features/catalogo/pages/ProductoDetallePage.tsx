import { useState } from 'react'
import { Link, useParams } from 'react-router'
import { toApiError } from '@/shared/api/errors'
import { EstadoVacio } from '@/shared/components/EstadoVacio'
import { Skeleton } from '@/shared/components/Skeleton'
import { formatearDinero, urlDeMedia } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { Checkbox } from '@/shared/ui/Checkbox'
import { useCartStore } from '@/store/cartStore'
import { useUiStore } from '@/store/uiStore'
import { useProductoDetalle } from '../hooks/useCatalogo'
import type { ProductoDetalle } from '../types'

/** Detalle y personalización: el cliente quita los ingredientes removibles ("sin cebolla") y elige la cantidad. */
export default function ProductoDetallePage() {
  const { id } = useParams()
  const { data, isLoading, isError, error } = useProductoDetalle(Number(id))

  if (isLoading) return <Skeleton className="h-96 w-full rounded-xl" />
  if (isError || !data) {
    const noExiste = toApiError(error).status === 404
    return (
      <div className="rounded-xl border border-surface-border bg-white">
        <EstadoVacio
          titulo={
            noExiste ? 'Este producto ya no está disponible' : 'No pudimos cargar el producto'
          }
          descripcion={
            noExiste ? 'Puede que lo hayamos retirado de la carta.' : toApiError(error).message
          }
          accion={
            <Link to={RUTAS.inicio} className="font-semibold text-accent-700 underline">
              Volver a la carta
            </Link>
          }
        />
      </div>
    )
  }
  // key: al cambiar de producto se reinicia la personalización.
  return <Detalle key={data.id} producto={data} />
}

function Detalle({ producto }: { producto: ProductoDetalle }) {
  const [quitados, setQuitados] = useState<number[]>([])
  const [cantidad, setCantidad] = useState(1)
  const addItem = useCartStore((s) => s.addItem)
  const abrirCarrito = useUiStore((s) => s.setCartOpen)
  const imagen = urlDeMedia(producto.imagen_url)
  const total = Number(producto.precio_base) * cantidad

  function alternar(id: number) {
    setQuitados((q) => (q.includes(id) ? q.filter((x) => x !== id) : [...q, id]))
  }

  function agregar() {
    addItem({
      productoId: producto.id,
      nombre: producto.nombre,
      precio: Number(producto.precio_base),
      cantidad,
      exclusiones: quitados,
      exclusionesNombres: producto.ingredientes
        .filter((i) => quitados.includes(i.ingrediente_id))
        .map((i) => i.nombre),
    })
    abrirCarrito(true)
  }

  return (
    <div className="flex flex-col gap-4">
      <nav aria-label="Ruta de navegación">
        <Link to={RUTAS.inicio} className="text-sm font-semibold text-accent-700 underline">
          ← Volver a la carta
        </Link>
      </nav>
      <div className="grid gap-8 md:grid-cols-2">
        {imagen ? (
          <img
            src={imagen}
            alt={`Foto de ${producto.nombre}`}
            className="aspect-[4/3] w-full rounded-xl object-cover"
          />
        ) : (
          <div className="flex aspect-[4/3] w-full items-center justify-center rounded-xl bg-surface-border text-navy-700">
            Sin foto
          </div>
        )}
        <div className="flex flex-col gap-4">
          <div>
            <h1 className="text-3xl font-extrabold text-navy-900">{producto.nombre}</h1>
            <p className="mt-1 text-2xl font-extrabold text-navy-900">
              {formatearDinero(producto.precio_base)}
            </p>
          </div>
          {producto.descripcion && <p className="text-navy-700">{producto.descripcion}</p>}
          {producto.alergenos.length > 0 && (
            <p className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-semibold text-navy-900">Contiene:</span>
              {producto.alergenos.map((a) => (
                <Badge key={a} tone="danger">
                  {a}
                </Badge>
              ))}
            </p>
          )}

          {producto.ingredientes.length > 0 && (
            <fieldset className="flex flex-col gap-2 rounded-xl border border-surface-border bg-white p-4">
              <legend className="px-1 text-sm font-bold text-navy-900">Ingredientes</legend>
              {producto.ingredientes.map((i) =>
                i.es_removible ? (
                  <Checkbox
                    key={i.ingrediente_id}
                    label={`Sin ${i.nombre}`}
                    hint={i.es_alergeno ? 'Alérgeno' : undefined}
                    checked={quitados.includes(i.ingrediente_id)}
                    onChange={() => alternar(i.ingrediente_id)}
                  />
                ) : (
                  <p key={i.ingrediente_id} className="text-sm text-navy-700">
                    {i.nombre}
                    {i.es_alergeno && ' (alérgeno)'}{' '}
                    <span className="text-navy-500">· no se puede quitar</span>
                  </p>
                ),
              )}
            </fieldset>
          )}

          {producto.disponible ? (
            <div className="flex flex-wrap items-center gap-4">
              <div
                role="group"
                aria-label="Cantidad"
                className="inline-flex items-center rounded-lg border border-surface-border bg-white"
              >
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Quitar una unidad"
                  disabled={cantidad <= 1}
                  onClick={() => setCantidad((c) => c - 1)}
                >
                  −
                </Button>
                <span aria-live="polite" className="min-w-8 text-center font-bold">
                  {cantidad}
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label="Agregar una unidad"
                  disabled={cantidad >= 99}
                  onClick={() => setCantidad((c) => c + 1)}
                >
                  +
                </Button>
              </div>
              <Button onClick={agregar}>Agregar al carrito · {formatearDinero(total)}</Button>
            </div>
          ) : (
            <p
              role="status"
              className="rounded-lg bg-surface-border px-3 py-2 text-sm font-semibold text-navy-900"
            >
              Este producto no está disponible por ahora.
            </p>
          )}
        </div>
      </div>
    </div>
  )
}
