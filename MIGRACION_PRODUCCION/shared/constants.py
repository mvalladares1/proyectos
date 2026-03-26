"""
Constantes compartidas del sistema
"""

# Mapeo de meses
MESES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
}

# Colores para gráficos
COLORES = {
    'verde': '#28a745',
    'rojo': '#dc3545',
    'azul': '#1f77b4',
    'naranja': '#ff7f0e',
    'amarillo': '#ffc107',
    'gris': '#6c757d'
}

# Estados de Odoo
ESTADOS_PRODUCCION = {
    'draft': 'Borrador',
    'confirmed': 'Confirmado',
    'progress': 'En Progreso',
    'to_close': 'Por Cerrar',
    'done': 'Hecho',
    'cancel': 'Cancelado'
}

ESTADOS_STOCK = {
    'draft': 'Borrador',
    'waiting': 'Esperando',
    'confirmed': 'Confirmado',
    'assigned': 'Asignado',
    'done': 'Hecho',
    'cancel': 'Cancelado'
}

# Categorías de productos (IDs de Odoo)
CATEGORIAS = {
    'bandejas_productor': 107  # BANDEJAS A PRODUCTOR
}
