import { Outlet } from 'react-router'
import { Footer } from './Footer'
import { Header } from './Header'

export function PublicLayout({
  onLogout,
  loggingOut,
}: {
  onLogout: () => void
  loggingOut?: boolean
}) {
  return (
    <div className="flex min-h-screen flex-col">
      <Header onLogout={onLogout} loggingOut={loggingOut} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  )
}
