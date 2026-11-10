import { Link } from 'react-router'
import { RUTAS } from '@/shared/lib/rutas'
import { useAuthStore } from '@/store/authStore'

/** Portada provisoria: el catálogo con filtros, carrito y checkout llega en la Fase 3. */
export default function Home() {
  const usuario = useAuthStore((s) => s.usuario)
  return (
    <section className="flex flex-col items-start gap-4 py-8">
      <h1 className="text-3xl font-extrabold text-navy-900 sm:text-4xl">
        {usuario ? `Hola, ${usuario.nombre}` : 'Pedí tu comida favorita'}
      </h1>
      <p className="max-w-xl text-navy-700">
        Food Store reúne el catálogo, el carrito y el seguimiento de tus pedidos. El catálogo estará
        disponible próximamente.
      </p>
      {!usuario && (
        <Link
          to={RUTAS.registro}
          className="rounded-lg bg-accent-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-accent-700"
        >
          Crear mi cuenta
        </Link>
      )}
    </section>
  )
}
