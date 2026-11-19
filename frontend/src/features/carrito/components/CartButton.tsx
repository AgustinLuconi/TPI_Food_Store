import { Button } from '@/shared/ui/Button'
import { useCartStore } from '@/store/cartStore'
import { useUiStore } from '@/store/uiStore'

/** Botón del header con la cantidad de unidades. Se suscribe por selector: solo se redibuja si cambia el conteo. */
export function CartButton() {
  const cantidad = useCartStore((s) => s.itemCount())
  const abrir = useUiStore((s) => s.setCartOpen)
  return (
    <Button variant="secondary" size="sm" onClick={() => abrir(true)}>
      Carrito
      <span className="rounded-full bg-navy-900 px-2 text-xs font-bold text-white">{cantidad}</span>
      <span className="sr-only">
        {cantidad === 1 ? 'unidad en el carrito' : 'unidades en el carrito'}
      </span>
    </Button>
  )
}
