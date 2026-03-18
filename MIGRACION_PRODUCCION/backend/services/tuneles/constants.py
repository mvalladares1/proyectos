"""
Constantes y configuraciones para túneles estáticos.
"""

# Configuración de túneles y productos
TUNELES_CONFIG = {
    'TE1': {
        'producto_proceso_id': 15984,
        'producto_proceso_nombre': '[1.1] PROCESO CONGELADO TÚNEL ESTÁTICO 1',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 1',
        'picking_type_id': 192  # Rio Futuro: Congelar TE1 → RF/MO/CongTE1/XXXXX
    },
    'TE2': {
        'producto_proceso_id': 15985,
        'producto_proceso_nombre': '[1.2] PROCESO CONGELADO TÚNEL ESTÁTICO 2',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 2',
        'picking_type_id': 190  # Rio Futuro: Congelar TE2 → RF/MO/CongTE2/XXXXX
    },
    'TE3': {
        'producto_proceso_id': 15986,
        'producto_proceso_nombre': '[1.3] PROCESO CONGELADO TÚNEL ESTÁTICO 3',
        'sucursal': 'RF',
        'ubicacion_origen_id': 5452,
        'ubicacion_origen_nombre': 'RF/Stock/Camara 0°C REAL',
        'ubicacion_destino_id': 8479,
        'ubicacion_destino_nombre': 'Tránsito/Salida Túneles Estáticos',
        'sala_proceso': 'Tunel - Estatico 3',
        'picking_type_id': 191  # Rio Futuro: Congelar TE3 → RF/MO/CongTE3/XXXXX
    },
    'VLK': {
        'producto_proceso_id': 16446,
        'producto_proceso_nombre': '[1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK',
        'sucursal': 'VLK',
        'ubicacion_origen_id': 8528,
        'ubicacion_origen_nombre': 'VLK/Camara 0°',
        'ubicacion_destino_id': 8532,
        'ubicacion_destino_nombre': 'Tránsito VLK/Salida Túnel Estático',
        'sala_proceso': 'Tunel - Estatico VLK',
        'picking_type_id': 219  # VILKUN: Congelar TE VLK → MO/CongTE/XXXXX
    }
}

# Mapeo de productos: fresco → congelado
PRODUCTOS_TRANSFORMACION = {
    15999: 16183,  # [102122000] FB MK Conv. IQF en Bandeja → [202122000] FB MK Conv. IQF Congelado en Bandeja
    16016: 16182,  # [102121000] FB S/V Conv. IQF en Bandeja → [202121000] FB S/V Conv. IQF Congelado en Bandeja
}

# Provisión eléctrica
PRODUCTO_ELECTRICIDAD_ID = 15995  # [ETE] Provisión Electricidad Túnel Estático ($/hr)
UOM_DOLARES_KG_ID = 210  # $/Kg - UoM para provisión eléctrica

# Ubicaciones virtuales
UBICACION_VIRTUAL_CONGELADO_ID = 8485  # Virtual Locations/Ubicación Congelado
UBICACION_VIRTUAL_PROCESOS_ID = 15     # Virtual Locations/Ubicación Procesos
