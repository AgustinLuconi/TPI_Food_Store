import { useState } from 'react'
import { useUiStore } from '@/store/uiStore'
import { Button } from '@/shared/ui/Button'
import { Modal } from '@/shared/ui/Modal'

/**
 * Único lugar donde se renderiza el modal de confirmación del uiStore. Reemplaza a window.confirm()
 * (la regla `no-alert` de ESLint lo prohíbe). Se monta una sola vez en el layout raíz.
 */
export function ConfirmHost() {
  const confirm = useUiStore((s) => s.confirm)
  const closeConfirm = useUiStore((s) => s.closeConfirm)
  const [ejecutando, setEjecutando] = useState(false)

  async function aceptar() {
    if (!confirm) return
    setEjecutando(true)
    try {
      await confirm.onConfirm()
    } finally {
      setEjecutando(false)
      closeConfirm()
    }
  }

  return (
    <Modal
      open={confirm !== null}
      onClose={() => !ejecutando && closeConfirm()}
      title={confirm?.titulo ?? ''}
      footer={
        <>
          <Button variant="secondary" onClick={closeConfirm} disabled={ejecutando}>
            Cancelar
          </Button>
          <Button
            variant={confirm?.tono === 'danger' ? 'danger' : 'primary'}
            onClick={aceptar}
            loading={ejecutando}
          >
            {confirm?.confirmLabel ?? 'Confirmar'}
          </Button>
        </>
      }
    >
      <p className="text-sm text-navy-700">{confirm?.mensaje}</p>
    </Modal>
  )
}
