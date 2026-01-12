"""
Constantes para el módulo de Stock/Cámaras.
"""
from typing import Dict, List

# Configuración de ubicaciones específicas a mostrar
# Incluye cámaras RF y VLK
UBICACIONES_ESPECIFICAS: Dict[int, Dict] = {
    # RF/Stock
    5452: {"nombre": "Camara 0°C REAL", "capacidad": 200},
    8474: {"nombre": "Inventario Real", "capacidad": 500},
    # VLK - cámaras conocidas
    8528: {"nombre": "VLK/Camara 0°", "capacidad": 200},
    8497: {"nombre": "VLK/Stock", "capacidad": 500},
}

# Patrones para buscar cámaras VLK adicionales por nombre
VLK_PATRONES: List[Dict] = [
    {"patron": "Camara 1 -25", "capacidad": 200},
    {"patron": "Camara 2 -25", "capacidad": 200},
]

# Categorías que NO son productos de fruta (excluir del stock)
CATEGORIAS_EXCLUIDAS: List[str] = [
    "INVENTARIABLES", "BANDEJAS", "ACTIVO", "SERVICIOS",
    "EQUIPOS", "MUEBLES", "EJEMPLODS", "OTROS", "ALL1"
]

# TTL de caché para stocks
CACHE_TTL_PRODUCTOS = 1800  # 30 minutos
CACHE_TTL_UBICACIONES = 3600  # 1 hora
