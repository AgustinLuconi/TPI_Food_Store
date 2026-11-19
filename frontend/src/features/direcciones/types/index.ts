export interface Direccion {
  id: number
  alias: string | null
  linea1: string
  linea2: string | null
  ciudad: string | null
  provincia: string | null
  codigo_postal: string | null
  lat: number | null
  lng: number | null
  es_principal: boolean
}

export interface DireccionInput {
  alias: string | null
  linea1: string
  linea2: string | null
  ciudad: string | null
  provincia: string | null
  codigo_postal: string | null
  lat: number | null
  lng: number | null
  es_principal: boolean
}

export interface Punto {
  lat: number
  lng: number
}

/** Centro inicial del mapa (Buenos Aires, donde está el local del seed) cuando todavía no hay un punto elegido. */
export const CENTRO_POR_DEFECTO: Punto = { lat: -34.6037, lng: -58.3816 }
