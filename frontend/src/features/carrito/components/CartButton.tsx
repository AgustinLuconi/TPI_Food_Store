import { Button } from '@/shared/ui/Button'
import { useCartStore } from '@/store/cartStore'
import { useUiStore } from '@/store/uiStore'

/** Botón del header con la cantidad de unidades. Se suscribe por selector: solo se redibuja si cambia el conteo. */
export function CartButton() {
  const cantidad = useCartStore((s) => s.itemCount())
  const abrir = useUiStore((s) => s.setCartOpen)
  return (
    <Button
      variant="secondary"
      size="sm"
      onClick={() => abrir(true)}
      aria-label={`Abrir el carrito (${cantidad} ${cantidad === 1 ? 'unidad' : 'unidades'})`}
    >
      Carrito
      <span
        aria-hidden="true"
        className="rounded-full bg-accent-600 px-2 text-xs font-bold text-white"
      >
        {cantidad}
      </span>
    </Button>
  )
}
