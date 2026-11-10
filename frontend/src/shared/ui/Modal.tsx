import { useEffect, useId, useRef, type ReactNode } from 'react'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}

/**
 * Modal sobre el elemento <dialog> nativo: el navegador aporta el focus trap, el cierre con Esc
 * y el aislamiento del resto de la página (aria-modal implícito).
 */
export function Modal({ open, onClose, title, children, footer }: ModalProps) {
  const ref = useRef<HTMLDialogElement>(null)
  const titleId = useId()

  useEffect(() => {
    const dialog = ref.current
    if (!dialog) return
    if (open && !dialog.open) dialog.showModal()
    if (!open && dialog.open) dialog.close()
  }, [open])

  return (
    <dialog
      ref={ref}
      aria-labelledby={titleId}
      onCancel={(e) => {
        e.preventDefault() // el estado `open` lo controla el padre
        onClose()
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose() // clic en el fondo
      }}
      className="m-auto w-[calc(100%-2rem)] max-w-lg rounded-xl border border-surface-border bg-white p-0 text-navy-900 shadow-xl backdrop:bg-navy-900/50"
    >
      {open && (
        <div className="flex flex-col">
          <header className="border-b border-surface-border px-6 py-4">
            <h2 id={titleId} className="text-lg font-bold text-navy-900">
              {title}
            </h2>
          </header>
          <div className="max-h-[70vh] overflow-y-auto px-6 py-5">{children}</div>
          {footer && (
            <footer className="flex justify-end gap-3 border-t border-surface-border px-6 py-4">
              {footer}
            </footer>
          )}
        </div>
      )}
    </dialog>
  )
}
