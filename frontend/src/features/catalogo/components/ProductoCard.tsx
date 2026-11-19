import { Link } from 'react-router'
import { formatearDinero, urlDeMedia } from '@/shared/lib/formato'
import { RUTAS } from '@/shared/lib/rutas'
import { Badge } from '@/shared/ui/Badge'
import { Button } from '@/shared/ui/Button'
import { useCartStore } from '@/store/cartStore'
import { useUiStore } from '@/store/uiStore'
import type { ProductoItem } from '../types'

/** Tarjeta del catálogo del cliente. Agregar abre el carrito: el resultado se ve, sin notificaciones efímeras. */
export function ProductoCard({ producto }: { producto: ProductoItem }) {
  const addItem = useCartStore((s) => s.addItem)
  const abrirCarrito = useUiStore((s) => s.setCartOpen)
  const imagen = urlDeMedia(producto.imagen_url)

  function agregar() {
    addItem({
      productoId: producto.id,
      nombre: producto.nombre,
      precio: Number(producto.precio_base),
      exclusiones: [],
    })
    abrirCarrito(true)
  }

  return (
    <article className="flex flex-col overflow-hidden rounded-xl border border-surface-border bg-white shadow-sm">
      <Link
        to={RUTAS.producto(producto.id)}
        className="block"
        aria-label={`Ver ${producto.nombre}`}
      >
        {imagen ? (
          <img
            src={imagen}
            alt=""
            loading="lazy"
            className={`aspect-[4/3] w-full object-cover ${producto.disponible ? '' : 'opacity-50 grayscale'}`}
          />
        ) : (
          <div className="flex aspect-[4/3] w-full items-center justify-center bg-surface-border text-navy-700">
            <svg
              aria-hidden="true"
              viewBox="0 0 24 24"
              className="size-10 fill-none stroke-current"
              strokeWidth="1.5"
            >
              <rect x="3" y="4" width="18" height="16" rx="2" />
              <circle cx="9" cy="10" r="1.5" />
              <path d="m4 18 5-5 4 4 3-3 4 4" />
            </svg>
          </div>
        )}
      </Link>
      <div className="flex flex-1 flex-col gap-2 p-4">
        <div className="flex items-start justify-between gap-2">
          <h3 className="font-bold text-navy-900">
            <Link to={RUTAS.producto(producto.id)} className="hover:underline">
              {producto.nombre}
            </Link>
          </h3>
          {!producto.disponible && <Badge>No disponible</Badge>}
        </div>
        {producto.descripcion && (
          <p className="line-clamp-2 text-sm text-navy-500">{producto.descripcion}</p>
        )}
        <p className="mt-auto text-lg font-extrabold text-navy-900">
          {formatearDinero(producto.precio_base)}
        </p>
        <Button
          onClick={agregar}
          disabled={!producto.disponible}
          aria-label={`Agregar ${producto.nombre} al carrito`}
        >
          Agregar
        </Button>
      </div>
    </article>
  )
}
