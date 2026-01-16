"""
Constantes para servicio de rendimiento.
"""

# Categorías a excluir del consumo MP
EXCLUDED_CATEGORIES = ["insumo", "envase", "etiqueta", "embalaje", "merma"]

# Salas de proceso (vaciado) - Genera merma real
SALAS_PROCESO = [
    'sala 1', 'sala 2', 'sala 3', 'sala 4', 'sala 5', 'sala 6',
    'sala vilkun', 'vilkun',
    'linea retail', 'granel', 'proceso', 'sin sala'
]

# Mapeo de frutas
FRUIT_MAPPING = {
    'arándano': 'Arándano', 'arandano': 'Arándano', 'blueberr': 'Arándano',
    'frambuesa': 'Frambuesa', 'raspberry': 'Frambuesa', 'raspberr': 'Frambuesa',
    'mora': 'Mora', 'blackberr': 'Mora',
    'frutilla': 'Frutilla', 'fresa': 'Frutilla', 'strawberr': 'Frutilla',
    'cereza': 'Cereza', 'cherry': 'Cereza', 'guinda': 'Cereza',
    'kiwi': 'Kiwi',
    'manzana': 'Manzana', 'apple': 'Manzana',
}

# Indicadores de costos operacionales
OPERATIONAL_INDICATORS = [
    "provisión electricidad", "provisión electr",
    "túnel estático", "tunel estatico",
    "electricidad túnel", "costo hora", "($/hr)", "($/h)"
]

# Indicadores de packaging puro
PURE_PACKAGING = [
    "caja de exportación", "cajas de exportación", 
    "insumo", "envase", "pallet", "etiqueta", "doy pe"
]
