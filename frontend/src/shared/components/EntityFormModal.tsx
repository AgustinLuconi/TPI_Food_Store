import type { FormEvent, ReactNode } from 'react'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'

interface EntityFormModalProps {
  open: boolean
  /** Alta o edición: el mismo formulario sirve para ambos modos. */
  mode: 'create' | 'edit'
  entityName: string
  onClose: () => void
  onSubmit: () => void
  isSubmitting?: boolean
  /** Error general del servidor (los errores de campo los muestra cada Input). */
  error?: string | null
  children: ReactNode
}

export function EntityFormModal({
  open,
  mode,
  entityName,
  onClose,
  onSubmit,
  isSubmitting = false,
  error,
  children,
}: EntityFormModalProps) {
  const formId = `form-${entityName.toLowerCase().replace(/\s+/g, '-')}`

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    onSubmit()
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={mode === 'create' ? `Agregar ${entityName}` : `Modificar ${entityName}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancelar
          </Button>
          <Button type="submit" form={formId} loading={isSubmitting}>
            {mode === 'create' ? 'Agregar' : 'Guardar cambios'}
          </Button>
        </>
      }
    >
      <form id={formId} onSubmit={handleSubmit} noValidate className="flex flex-col gap-4">
        {children}
        {error && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-danger-700">
            {error}
          </p>
        )}
      </form>
    </Modal>
  )
}
