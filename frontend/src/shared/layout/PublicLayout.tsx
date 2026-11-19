import type { ReactNode } from 'react'
import { Outlet } from 'react-router'
import { Footer } from './Footer'
import { Header } from './Header'

export function PublicLayout({
  onLogout,
  loggingOut,
  acciones,
  children,
}: {
  onLogout: () => void
  loggingOut?: boolean
  acciones?: ReactNode
  /** Elementos globales de la tienda (por ejemplo, el panel del carrito). */
  children?: ReactNode
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header onLogout={onLogout} loggingOut={loggingOut} acciones={acciones} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <Footer />
      {children}
    </div>
  )
}
