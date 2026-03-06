"""
Constantes y estructura del Estado de Flujo de Efectivo NIIF IAS 7.
"""

# Concepto fallback para cuentas sin mapear
CONCEPTO_FALLBACK = "1.2.6"  # Otras entradas (salidas) de efectivo

# Estructura IAS 7 para Actividades - FUENTE DE VERDAD
# Solo Operación por ahora (FASE 1)
ESTRUCTURA_FLUJO = {
    "OPERACION": {
        "nombre": "1. Flujos de efectivo procedentes (utilizados) en actividades de operación",
        "lineas": [
            {"codigo": "1.1.1", "nombre": "Cobros procedentes de las ventas de bienes y prestación de servicios", "signo": 1},
            {"codigo": "1.2.1", "nombre": "Pagos a proveedores por el suministro de bienes y servicios", "signo": -1},
            {"codigo": "1.2.2", "nombre": "Pagos a y por cuenta de los empleados", "signo": -1},
            {"codigo": "1.2.3", "nombre": "Intereses pagados", "signo": -1},
            {"codigo": "1.2.4", "nombre": "Intereses recibidos", "signo": 1},
            {"codigo": "1.2.5", "nombre": "Impuestos a las ganancias reembolsados (pagados)", "signo": -1},
            {"codigo": "1.2.6", "nombre": "Otras entradas (salidas) de efectivo", "signo": 1}
        ],
        "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados en) actividades de operación"
    },
    "INVERSION": {
        "nombre": "2. Flujos de efectivo procedentes de (utilizados) en actividades de inversión",
        "lineas": [],
        "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados) en actividades de inversión"
    },
    "FINANCIAMIENTO": {
        "nombre": "3. Flujos de efectivo procedentes de (utilizados) en actividades de financiamiento",
        "lineas": [
            {"codigo": "3.0.1", "nombre": "Importes procedentes de préstamos de largo plazo", "signo": 1},
            {"codigo": "3.0.2", "nombre": "Importes procedentes de préstamos de corto plazo", "signo": 1},
            {"codigo": "3.1.1", "nombre": "Préstamos de entidades relacionadas", "signo": 1},
            {"codigo": "3.1.4", "nombre": "Pagos de pasivos por arrendamientos financieros", "signo": -1}
        ],
        "subtotal_nombre": "Flujos de efectivo netos procedentes de (utilizados) en actividades de financiamiento"
    }
}

# Mapeo OBLIGATORIO de cuentas de financiamiento (Parametrización Fija)
CUENTAS_FIJAS_FINANCIAMIENTO = {
    # 3.0.2 Importes procedentes de préstamos de corto plazo
    "21010101": "3.0.2", "21010103": "3.0.2", "82010101": "3.0.2",
    # 3.0.1 Importes procedentes de préstamos de largo plazo
    "21010213": "3.0.1", "21010223": "3.0.1", "22010101": "3.0.1",
    # 3.1.1 Préstamos de entidades relacionadas
    "21030201": "3.1.1", "21030211": "3.1.1", "22020101": "3.1.1",
    # 3.1.4 Pagos de pasivos por arrendamientos financieros
    "21010201": "3.1.4", "21010202": "3.1.4", "21010204": "3.1.4",
    "22010202": "3.1.4", "22010204": "3.1.4", "82010102": "3.1.4"
}

# Cuentas reclasificadas a 1.2.6 (Otras entradas/salidas de efectivo - Operación)
CUENTAS_RECLASIFICAR_126 = {
    "21010102": "1.2.6"  # Reclasificada desde 3.0.2 a Operación
}

# Cuentas a EXCLUIR completamente del flujo de caja
CUENTAS_EXCLUIR_FLUJO = [
    "21020101",  # Excluir del flujo
    "11060101",  # Excluir del flujo
    "62010101",  # Excluir del flujo
]

# Cuentas que deben aparecer en "Facturas Proyectadas (Módulo Contabilidad)"
# independiente de qué diario provengan
CUENTAS_DESTINO_PROYECTADAS_CONTAB = [
    "11060108",  # Redirigir a Proyectadas Contabilidad
]

# Categorías técnicas especiales
CATEGORIA_NEUTRAL = "NEUTRAL"       # No impacta flujo (transferencias internas)
CATEGORIA_PENDIENTE = "PENDIENTE"   # Sin clasificar (va a 1.2.6 + lista pendientes)
CATEGORIA_UNCLASSIFIED = "1.2.6"    # Otras entradas (salidas) de efectivo - fallback
CATEGORIA_FX_EFFECT = "4.2"         # Efectos variación tipo de cambio

# Emojis por actividad
EMOJIS_ACTIVIDAD = {
    "OPERACION": "🟢",
    "INVERSION": "🔵",
    "FINANCIAMIENTO": "🟣",
    "CONCILIACION": "⚪"
}
