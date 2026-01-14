"""
Constantes para el Estado de Resultados Expandible.
Define la estructura jerárquica del EERR con 3 niveles.
"""

# Estructura del Estado de Resultados con niveles
# Nivel 1: Categoría principal (1 - INGRESOS, 2 - COSTOS, etc.)
# Nivel 2: Subcategoría
# Nivel 3: Cuenta contable

ESTRUCTURA_EERR = [
    {
        "id": "1",
        "nombre": "INGRESOS",
        "tipo": "CATEGORIA",
        "icono": "💰",
        "signo": 1,  # Positivo
        "calculado": False,
    },
    {
        "id": "2",
        "nombre": "COSTOS",
        "tipo": "CATEGORIA",
        "icono": "📦",
        "signo": -1,  # Negativo
        "calculado": False,
    },
    {
        "id": "3",
        "nombre": "UTILIDAD BRUTA",
        "tipo": "SUBTOTAL",
        "icono": "🟦",
        "formula": "1 - 2",
        "calculado": True,
    },
    {
        "id": "4",
        "nombre": "GASTOS DIRECTOS",
        "tipo": "CATEGORIA",
        "icono": "🔧",
        "signo": -1,
        "calculado": False,
    },
    {
        "id": "5",
        "nombre": "MARGEN DE CONTRIBUCIÓN",
        "tipo": "SUBTOTAL",
        "icono": "🟦",
        "formula": "3 - 4",
        "calculado": True,
    },
    {
        "id": "6",
        "nombre": "GAV",
        "tipo": "CATEGORIA",
        "icono": "🏢",
        "signo": -1,
        "calculado": False,
    },
    {
        "id": "7",
        "nombre": "UTILIDAD OPERACIONAL (EBIT)",
        "tipo": "SUBTOTAL",
        "icono": "🟦",
        "formula": "5 - 6",
        "calculado": True,
    },
    {
        "id": "8",
        "nombre": "INTERESES",
        "tipo": "CATEGORIA",
        "icono": "🏦",
        "signo": -1,
        "calculado": False,
    },
    {
        "id": "9",
        "nombre": "UTILIDAD ANTES DE NO OP.",
        "tipo": "SUBTOTAL",
        "icono": "🟦",
        "formula": "7 - 8",
        "calculado": True,
    },
    {
        "id": "10",
        "nombre": "INGRESOS NO OPERACIONALES",
        "tipo": "CATEGORIA",
        "icono": "➕",
        "signo": 1,
        "calculado": False,
    },
    {
        "id": "11",
        "nombre": "GASTOS NO OPERACIONALES",
        "tipo": "CATEGORIA",
        "icono": "➖",
        "signo": -1,
        "calculado": False,
    },
    {
        "id": "12",
        "nombre": "RESULTADO NO OPERACIONAL",
        "tipo": "SUBTOTAL",
        "icono": "🟦",
        "formula": "10 - 11",
        "calculado": True,
    },
    {
        "id": "13",
        "nombre": "UTILIDAD ANTES DE IMPUESTOS",
        "tipo": "TOTAL",
        "icono": "🟩",
        "formula": "9 + 12",
        "calculado": True,
    },
]

# Colores para valores
EERR_COLORS = {
    "positive": "#10b981",      # Verde
    "negative": "#ef4444",      # Rojo
    "neutral": "#6b7280",       # Gris
    "subtotal_bg": "#1e293b",   # Fondo subtotales
    "total_bg": "#0f172a",      # Fondo totales
    "hover": "#334155",         # Hover
    "border": "#374151",        # Bordes
}

# Mapeo de categorías a claves de datos del backend
CATEGORIA_MAP = {
    "1": "1 - INGRESOS",
    "2": "2 - COSTOS",
    "4": "4 - GASTOS DIRECTOS",
    "6": "6 - GAV",
    "8": "8 - INTERESES",
    "10": "10 - INGRESOS NO OPERACIONALES",
    "11": "11 - GASTOS NO OPERACIONALES",
}

# Nombres de meses
MESES_NOMBRES = {
    "01": "ENE", "02": "FEB", "03": "MAR", "04": "ABR",
    "05": "MAY", "06": "JUN", "07": "JUL", "08": "AGO",
    "09": "SEP", "10": "OCT", "11": "NOV", "12": "DIC"
}
