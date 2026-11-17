import { useState } from 'react'
import { toApiError } from '@/shared/api/errors'
import { EntityFormModal } from '@/shared/components/EntityFormModal'
import { urlDeMedia } from '@/shared/lib/formato'
import { Checkbox } from '@/shared/ui/Checkbox'
import { Input } from '@/shared/ui/Input'
import { Select } from '@/shared/ui/Select'
import { useGuardarProducto, useOpcionesDeCategoria } from '../hooks/useCatalogo'
import type { ProductoItem } from '../types'

interface Props {
  /** null = alta; con valor = edición. */
  producto: ProductoItem | null
  onClose: () => void
  onSaved: (guardado: ProductoItem, modo: 'create' | 'edit') => void
}

const TIPOS_IMAGEN = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 2 * 1024 * 1024

export function ProductoFormModal({ producto, onClose, onSaved }: Props) {
  const mode = producto ? 'edit' : 'create'
  const [nombre, setNombre] = useState(producto?.nombre ?? '')
  const [descripcion, setDescripcion] = useState(producto?.descripcion ?? '')
  const [precio, setPrecio] = useState(producto?.precio_base ?? '')
  const [stockMinimo, setStockMinimo] = useState(String(producto?.stock_minimo ?? 0))
  const [categoriaIds, setCategoriaIds] = useState<number[]>(
    producto?.categorias.map((c) => c.id) ?? [],
  )
  const [principalId, setPrincipalId] = useState(
    producto?.categorias.find((c) => c.es_principal)?.id.toString() ?? '',
  )
  const [imagen, setImagen] = useState<File | null>(null)
  const [errores, setErrores] = useState<Record<string, string>>({})

  const guardar = useGuardarProducto()
  const { data: categorias = [] } = useOpcionesDeCategoria()

  function alternarCategoria(id: number) {
    setCategoriaIds((actuales) => {
      const nuevas = actuales.includes(id) ? actuales.filter((c) => c !== id) : [...actuales, id]
      if (!nuevas.includes(Number(principalId))) setPrincipalId('')
      return nuevas
    })
  }

  function elegirImagen(archivo: File | undefined) {
    if (!archivo) return setImagen(null)
    if (!TIPOS_IMAGEN.includes(archivo.type)) {
      setImagen(null)
      return setErrores((e) => ({ ...e, imagen: 'La imagen debe ser JPEG, PNG o WEBP' }))
    }
    if (archivo.size > MAX_BYTES) {
      setImagen(null)
      return setErrores((e) => ({ ...e, imagen: 'La imagen no puede superar los 2 MB' }))
    }
    setErrores((e) => ({ ...e, imagen: '' }))
    setImagen(archivo)
  }

  function enviar() {
    const nuevos: Record<string, string> = {}
    if (!nombre.trim()) nuevos.nombre = 'Ingresá un nombre'
    if (!/^\d+(\.\d{1,2})?$/.test(precio.trim()))
      nuevos.precio = 'Ingresá un precio válido (hasta 2 decimales)'
    if (!/^\d+$/.test(stockMinimo)) nuevos.stockMinimo = 'Ingresá un número entero (0 o más)'
    setErrores(nuevos)
    if (Object.keys(nuevos).length > 0) return

    guardar.mutate(
      {
        id: producto?.id,
        imagen,
        input: {
          nombre: nombre.trim(),
          descripcion: descripcion.trim() || null,
          precio_base: precio.trim(),
          stock_minimo: Number(stockMinimo),
          categoria_ids: categoriaIds,
          categoria_principal_id: principalId ? Number(principalId) : null,
        },
      },
      { onSuccess: (guardado) => onSaved(guardado, mode) },
    )
  }

  const error = guardar.error ? toApiError(guardar.error) : null
  const deCampo = (campo: string) => (error?.field === campo ? error.message : undefined)
  const opcionesPrincipal = [
    { value: '', label: 'La primera que elija' },
    ...categorias
      .filter((c) => categoriaIds.includes(c.id))
      .map((c) => ({ value: String(c.id), label: c.ruta })),
  ]
  const actual = urlDeMedia(producto?.imagen_url)

  return (
    <EntityFormModal
      open
      mode={mode}
      entityName="producto"
      onClose={onClose}
      onSubmit={enviar}
      isSubmitting={guardar.isPending}
      error={error && !error.field ? error.message : null}
    >
      <Input
        label="Nombre"
        required
        maxLength={200}
        value={nombre}
        onChange={(e) => setNombre(e.target.value)}
        error={errores.nombre ?? deCampo('nombre')}
      />
      <Input
        label="Descripción"
        value={descripcion}
        onChange={(e) => setDescripcion(e.target.value)}
      />
      <div className="grid grid-cols-2 gap-4">
        <Input
          label="Precio"
          required
          inputMode="decimal"
          value={precio}
          onChange={(e) => setPrecio(e.target.value)}
          error={errores.precio ?? deCampo('precio_base')}
        />
        <Input
          label="Stock mínimo"
          inputMode="numeric"
          value={stockMinimo}
          onChange={(e) => setStockMinimo(e.target.value)}
          error={errores.stockMinimo ?? deCampo('stock_minimo')}
        />
      </div>

      <fieldset className="flex flex-col gap-2">
        <legend className="mb-1 text-sm font-semibold text-navy-900">Categorías</legend>
        <div className="grid max-h-40 gap-2 overflow-y-auto rounded-lg border border-surface-border p-3">
          {categorias.length === 0 && (
            <p className="text-sm text-navy-500">No hay categorías activas.</p>
          )}
          {categorias.map((c) => (
            <Checkbox
              key={c.id}
              label={c.ruta}
              checked={categoriaIds.includes(c.id)}
              onChange={() => alternarCategoria(c.id)}
            />
          ))}
        </div>
        {deCampo('categoria_ids') && (
          <p className="text-sm text-danger-700">{deCampo('categoria_ids')}</p>
        )}
      </fieldset>
      <Select
        label="Categoría principal"
        value={principalId}
        options={opcionesPrincipal}
        onChange={(e) => setPrincipalId(e.target.value)}
        disabled={categoriaIds.length === 0}
      />

      <div className="flex flex-col gap-2">
        <Input
          label="Imagen"
          type="file"
          accept="image/jpeg,image/png,image/webp"
          hint="JPEG, PNG o WEBP de hasta 2 MB."
          onChange={(e) => elegirImagen(e.target.files?.[0])}
          error={errores.imagen || deCampo('archivo')}
        />
        {actual && !imagen && (
          <img
            src={actual}
            alt={`Imagen actual de ${producto?.nombre}`}
            className="h-24 w-24 rounded-lg object-cover"
          />
        )}
      </div>
    </EntityFormModal>
  )
}
