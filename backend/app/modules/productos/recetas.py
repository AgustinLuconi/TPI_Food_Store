"""Reglas puras de recetas (sin acceso a datos), fáciles de probar."""

from collections.abc import Iterable


def hay_ciclo(aristas: Iterable[tuple[int, int]], padre_id: int, componentes: Iterable[int]) -> bool:
    """RN-11: ¿agregar las aristas padre → componente cerraría un ciclo?

    `aristas` son los pares (padre, componente) que YA existen, sin los del padre que se está
    guardando. Se recorre en profundidad el grafo desde cada componente nuevo: si se llega al
    padre, esa receta terminaría contiéndose a sí misma (A usa B, B usa C, C usa A).
    """
    hijos: dict[int, list[int]] = {}
    for padre, componente in aristas:
        hijos.setdefault(padre, []).append(componente)

    visitados: set[int] = set()
    pendientes = list(componentes)
    while pendientes:
        actual = pendientes.pop()
        if actual == padre_id:
            return True
        if actual in visitados:
            continue
        visitados.add(actual)
        pendientes.extend(hijos.get(actual, []))
    return False
