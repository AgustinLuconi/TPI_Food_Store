import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { Card } from '@/shared/ui/Card'

/** Contenedor centrado de las pantallas de acceso (login y registro). */
export function AuthLayout({ titulo, children }: { titulo: string; children: ReactNode }) {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-10">
      <Link to="/" className="text-2xl font-extrabold text-navy-900">
        Food<span className="text-accent-700">Store</span>
      </Link>
      <Card className="w-full max-w-md p-6 sm:p-8">
        <h1 className="mb-6 text-xl font-bold text-navy-900">{titulo}</h1>
        {children}
      </Card>
    </main>
  )
}
