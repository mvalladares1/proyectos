# Estándar de Modularización del Backend

**Proyecto:** Rio Futuro Dashboards  
**Fecha:** 9 de Enero 2026  
**Versión:** 1.0

---

## 📋 Objetivo

Establecer criterios claros y patrones de modularización para el backend (FastAPI) que permitan:
- **Mantenibilidad**: Código fácil de entender y modificar
- **Escalabilidad**: Agregar funcionalidades sin aumentar complejidad
- **Testabilidad**: Aislar lógica para pruebas unitarias
- **Reutilización**: Compartir código entre módulos sin duplicación

---

## 🎯 Principios Fundamentales

### 1. Separación de Responsabilidades

Cada módulo debe tener **una sola responsabilidad clara**:

```
Router      → Orquestación de HTTP (validación, respuesta)
Service     → Lógica de negocio (cálculos, transformaciones)
Utils       → Funciones auxiliares reutilizables
Models      → Estructuras de datos (Pydantic)
```

### 2. Jerarquía de Dependencias

```
┌─────────────┐
│   Router    │  ← Solo llama a Service
└──────┬──────┘
       │
┌──────▼──────┐
│   Service   │  ← Llama a OdooClient, Utils, Cache
└──────┬──────┘
       │
┌──────▼──────┐
│ OdooClient  │  ← Capa de integración
└─────────────┘
```

**❌ NUNCA:**
- Router con lógica de negocio
- Service accediendo directamente a request/response
- Utils con estado mutable

### 3. Límites de Tamaño

| Componente | Líneas Máximas | Acción si se excede |
|------------|----------------|---------------------|
| **Router** | 300 líneas | Dividir en sub-routers |
| **Service** | 800 líneas | Extraer a sub-módulos |
| **Función** | 100 líneas | Refactorizar en funciones más pequeñas |
| **Método** | 50 líneas | Extraer helpers privados |

---

## 📁 Estructura de Modularización

### Caso 1: Service Simple (< 800 líneas)

**✅ Estructura actual (mantener):**
```
backend/services/
├── bandejas_service.py          (264 líneas)
├── permissions_service.py       (315 líneas)
└── presupuesto_service.py       (236 líneas)
```

### Caso 2: Service Grande (800-1500 líneas)

**⚠️ Necesita modularización:**

```
backend/services/
├── rendimiento/
│   ├── __init__.py              # Exporta clase principal
│   ├── service.py               # Clase principal + métodos públicos
│   ├── helpers.py               # Funciones auxiliares privadas
│   ├── calculators.py           # Lógica de cálculos específicos
│   └── constants.py             # Constantes y mapeos
```

**Ejemplo:** `rendimiento_service.py` (1306 líneas)

**Antes:**
```python
# backend/services/rendimiento_service.py (1306 líneas)
class RendimientoService:
    EXCLUDED_CATEGORIES = [...]
    SALAS_PROCESO = [...]
    
    def _is_operational_cost(self, product_name: str) -> bool:
        # 20 líneas de lógica
        ...
    
    def _extract_fruit_type(self, product_name: str) -> str:
        # 30 líneas de mapeo
        ...
    
    def _calcular_rendimiento(self, consumo, produccion):
        # 50 líneas de cálculos
        ...
    
    def get_dashboard_completo(self, ...):
        # 200 líneas de agregación
        ...
```

**Después:**
```python
# backend/services/rendimiento/__init__.py
from .service import RendimientoService

__all__ = ['RendimientoService']
```

```python
# backend/services/rendimiento/constants.py
"""Constantes y configuraciones del módulo de rendimiento."""

EXCLUDED_CATEGORIES = ["insumo", "envase", "etiqueta", "embalaje", "merma"]

SALAS_PROCESO = [
    'sala 1', 'sala 2', 'sala 3', 'sala 4', 'sala 5', 'sala 6',
    'linea retail', 'granel', 'proceso'
]

FRUIT_MAPPING = {
    'arándano': 'Arándano', 'arandano': 'Arándano',
    'frambuesa': 'Frambuesa', 'raspberry': 'Frambuesa',
    # ...
}
```

```python
# backend/services/rendimiento/helpers.py
"""Funciones auxiliares para clasificación de productos."""
from .constants import EXCLUDED_CATEGORIES, FRUIT_MAPPING

def is_operational_cost(product_name: str) -> bool:
    """Identifica costos operacionales."""
    if not product_name:
        return False
    
    name_lower = product_name.lower()
    operational_indicators = [
        "provisión electricidad", "túnel estático",
        "electricidad túnel", "costo hora"
    ]
    
    return any(ind in name_lower for ind in operational_indicators)

def is_excluded_consumo(product_name: str, category_name: str = '') -> bool:
    """Verifica si un producto debe excluirse del consumo MP."""
    # Lógica de exclusión
    ...

def extract_fruit_type(product_name: str) -> str:
    """Extrae el tipo de fruta del nombre del producto."""
    if not product_name:
        return 'Otro'
    
    name_lower = product_name.lower()
    for key, value in FRUIT_MAPPING.items():
        if key in name_lower:
            return value
    return 'Otro'
```

```python
# backend/services/rendimiento/calculators.py
"""Lógica de cálculos de rendimiento."""
from typing import Dict, List

def calcular_rendimiento_mo(consumos: List[Dict], produccion: float) -> Dict:
    """Calcula rendimiento de una orden de fabricación."""
    total_consumo = sum(c['qty'] for c in consumos)
    rendimiento = (produccion / total_consumo * 100) if total_consumo > 0 else 0
    
    return {
        'consumo_kg': total_consumo,
        'produccion_kg': produccion,
        'rendimiento_pct': round(rendimiento, 2)
    }

def consolidar_por_fruta(mos: List[Dict]) -> Dict:
    """Consolida rendimientos por tipo de fruta."""
    # Lógica de agregación
    ...
```

```python
# backend/services/rendimiento/service.py
"""Servicio principal de rendimiento productivo."""
from typing import Optional, Dict, List
from shared.odoo_client import OdooClient
from backend.cache import get_cache
from .helpers import is_excluded_consumo, extract_fruit_type
from .calculators import calcular_rendimiento_mo, consolidar_por_fruta

class RendimientoService:
    """Servicio para análisis de rendimiento productivo."""
    
    def __init__(self, username: str = None, password: str = None):
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def get_dashboard_completo(self, fecha_inicio: str, fecha_fin: str) -> Dict:
        """Obtiene datos consolidados del dashboard."""
        # Lógica principal que orquesta llamadas a helpers y calculators
        ...
    
    def get_trazabilidad_inversa(self, lote_pt: str) -> Dict:
        """Trazabilidad PT → MP."""
        ...
```

### Caso 3: Service Muy Grande (> 1500 líneas)

**🚨 Necesita división en múltiples services:**

```
backend/services/
├── tuneles/
│   ├── __init__.py
│   ├── validation_service.py    # Validaciones de túneles
│   ├── creation_service.py      # Creación de MOs
│   ├── monitoring_service.py    # Monitoreo de estado
│   ├── helpers.py               # Utilidades compartidas
│   └── constants.py             # Configuraciones
```

**Ejemplo:** `tuneles_service.py` (2252 líneas) → Dividir en 3 services

---

## 🔧 Patrones de Modularización

### Patrón 1: Extracción de Helpers

**Cuándo aplicar:** Funciones auxiliares repetidas o complejas

**Antes:**
```python
# backend/services/comercial_service.py
class ComercialService:
    def _format_currency(self, amount, currency='CLP'):
        if currency == 'USD':
            return f"${amount:,.2f}"
        return f"${amount:,.0f}".replace(',', '.')
    
    def _format_date(self, date_str):
        # Lógica de formateo
        ...
```

**Después:**
```python
# backend/utils/formatters.py
def format_currency(amount: float, currency: str = 'CLP') -> str:
    """Formatea montos monetarios."""
    if currency == 'USD':
        return f"${amount:,.2f}"
    return f"${amount:,.0f}".replace(',', '.')

def format_date(date_str: str, format: str = '%d-%m-%Y') -> str:
    """Formatea fechas."""
    ...

# backend/services/comercial_service.py
from backend.utils.formatters import format_currency, format_date

class ComercialService:
    # Usar funciones importadas
    ...
```

### Patrón 2: Extracción de Constantes

**Cuándo aplicar:** Listas, diccionarios, configuraciones que ocupan espacio

**Antes:**
```python
# backend/services/flujo_caja_service.py
class FlujoCajaService:
    def __init__(self):
        self.CATEGORIAS_OPERACION = {
            'cobros_clientes': ['Cobros por ventas', 'Factoring'],
            'pago_proveedores': ['Pago a proveedores', 'Pago servicios'],
            # ... 50 líneas más
        }
```

**Después:**
```python
# backend/services/flujo_caja/constants.py
CATEGORIAS_OPERACION = {
    'cobros_clientes': ['Cobros por ventas', 'Factoring'],
    'pago_proveedores': ['Pago a proveedores', 'Pago servicios'],
    # ... 50 líneas
}

# backend/services/flujo_caja/service.py
from .constants import CATEGORIAS_OPERACION

class FlujoCajaService:
    # Código más limpio
    ...
```

### Patrón 3: Extracción de Calculators

**Cuándo aplicar:** Lógica de cálculos complejos que no dependen del estado de la clase

**Antes:**
```python
class ReportService:
    def _calcular_indicadores_financieros(self, ventas, costos, gastos):
        # 80 líneas de cálculos
        margen_bruto = (ventas - costos) / ventas * 100
        margen_neto = (ventas - costos - gastos) / ventas * 100
        # ...
        return {...}
```

**Después:**
```python
# backend/services/report/calculators.py
from typing import Dict

def calcular_indicadores_financieros(
    ventas: float, 
    costos: float, 
    gastos: float
) -> Dict:
    """Calcula indicadores financieros."""
    margen_bruto = (ventas - costos) / ventas * 100 if ventas else 0
    margen_neto = (ventas - costos - gastos) / ventas * 100 if ventas else 0
    
    return {
        'margen_bruto': round(margen_bruto, 2),
        'margen_neto': round(margen_neto, 2)
    }

# backend/services/report/service.py
from .calculators import calcular_indicadores_financieros

class ReportService:
    def generar_reporte(self, ...):
        indicadores = calcular_indicadores_financieros(ventas, costos, gastos)
        ...
```

### Patrón 4: División de Routers

**Cuándo aplicar:** Router con más de 10 endpoints o 300 líneas

**Antes:**
```python
# backend/routers/automatizaciones.py (374 líneas)
router = APIRouter(prefix="/api/v1/automatizaciones")

@router.post("/crear-mo")
async def crear_mo(...): ...

@router.get("/monitorear")
async def monitorear(...): ...

@router.get("/tuneles")
async def get_tuneles(...): ...

# ... 8 endpoints más
```

**Después:**
```python
# backend/routers/automatizaciones/__init__.py
from fastapi import APIRouter
from .creacion import router as creacion_router
from .monitoreo import router as monitoreo_router
from .configuracion import router as configuracion_router

router = APIRouter(prefix="/api/v1/automatizaciones", tags=["automatizaciones"])

router.include_router(creacion_router)
router.include_router(monitoreo_router)
router.include_router(configuracion_router)

# backend/routers/automatizaciones/creacion.py
from fastapi import APIRouter
router = APIRouter()

@router.post("/crear-mo")
async def crear_mo(...): ...

@router.post("/validar-tunel")
async def validar_tunel(...): ...

# backend/routers/automatizaciones/monitoreo.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/monitorear")
async def monitorear(...): ...

@router.get("/estado/{mo_id}")
async def get_estado(...): ...
```

---

## ✅ Checklist de Modularización

### Antes de modularizar

- [ ] El archivo tiene más de 800 líneas (services) o 300 (routers)
- [ ] Identificar responsabilidades separables
- [ ] Revisar dependencias entre funciones
- [ ] Planificar estructura de carpetas

### Durante la modularización

- [ ] Crear estructura de carpetas `modulo/`
- [ ] Crear `__init__.py` con exports claros
- [ ] Mover constantes a `constants.py`
- [ ] Mover helpers a `helpers.py` o `utils/`
- [ ] Mover cálculos a `calculators.py`
- [ ] Mantener clase/router principal en `service.py` o `router.py`
- [ ] Actualizar imports en archivos que usan el módulo
- [ ] Agregar type hints a todas las funciones nuevas
- [ ] Agregar docstrings a funciones públicas

### Después de modularizar

- [ ] Ejecutar tests (si existen)
- [ ] Verificar que la API responde correctamente
- [ ] Revisar que no hay imports circulares
- [ ] Documentar cambios en CHANGELOG o docs/
- [ ] Code review con equipo

---

## 🎯 Prioridades de Modularización

Basado en análisis del código actual (Enero 2026):

### Prioridad ALTA 🔴

| Archivo | Líneas | Acción Recomendada |
|---------|--------|-------------------|
| `tuneles_service.py` | 2252 | Dividir en 3 services: validation, creation, monitoring |
| `flujo_caja_service.py` | 1551 | Extraer a submódulo: helpers, calculators, constants |
| `rendimiento_service.py` | 1306 | Extraer a submódulo: helpers, calculators, constants |
| `report_service.py` | 1206 | Dividir en 2-3 services por tipo de reporte |

### Prioridad MEDIA 🟡

| Archivo | Líneas | Acción Recomendada |
|---------|--------|-------------------|
| `compras_service.py` | 1031 | Extraer helpers y calculators |
| `containers_service.py` | 921 | Extraer helpers y constants |
| `stock_service.py` | 883 | Extraer calculators |
| `automatizaciones.py` (router) | 374 | Dividir en sub-routers |
| `flujo_caja.py` (router) | 285 | Dividir en sub-routers |
| `recepcion.py` (router) | 258 | Dividir en sub-routers |

### Prioridad BAJA 🟢

Servicios bien dimensionados (< 700 líneas): Mantener como están.

---

## 📝 Plantillas de Código

### Template: Service Modularizado

```python
# backend/services/mi_modulo/__init__.py
"""
Módulo de [Descripción].
"""
from .service import MiModuloService

__all__ = ['MiModuloService']
```

```python
# backend/services/mi_modulo/constants.py
"""Constantes y configuraciones."""

# Categorías
CATEGORIAS_PRINCIPALES = [...]

# Mapeos
MAPEO_ESTADOS = {
    'draft': 'Borrador',
    'confirmed': 'Confirmado',
}

# Configuraciones
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3
```

```python
# backend/services/mi_modulo/helpers.py
"""Funciones auxiliares."""
from typing import Optional

def validar_fecha(fecha_str: str) -> bool:
    """Valida formato de fecha YYYY-MM-DD."""
    try:
        datetime.strptime(fecha_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

def normalizar_nombre(nombre: str) -> str:
    """Normaliza nombre de producto."""
    return nombre.strip().lower()
```

```python
# backend/services/mi_modulo/calculators.py
"""Lógica de cálculos específicos."""
from typing import Dict, List

def calcular_totales(items: List[Dict]) -> Dict:
    """Calcula totales de una lista de items."""
    total_cantidad = sum(item.get('qty', 0) for item in items)
    total_monto = sum(item.get('amount', 0) for item in items)
    
    return {
        'total_cantidad': total_cantidad,
        'total_monto': total_monto,
        'promedio': total_monto / total_cantidad if total_cantidad else 0
    }
```

```python
# backend/services/mi_modulo/service.py
"""Servicio principal."""
from typing import Optional, Dict, List
from shared.odoo_client import OdooClient
from backend.cache import get_cache
from .helpers import validar_fecha, normalizar_nombre
from .calculators import calcular_totales
from .constants import CATEGORIAS_PRINCIPALES

class MiModuloService:
    """Servicio para gestión de [Módulo]."""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Inicializa el servicio.
        
        Args:
            username: Usuario Odoo
            password: API Key Odoo
        """
        self.odoo = OdooClient(username=username, password=password)
        self._cache = get_cache()
    
    def get_datos_principales(
        self, 
        fecha_inicio: str, 
        fecha_fin: str
    ) -> Dict:
        """
        Obtiene datos principales del módulo.
        
        Args:
            fecha_inicio: Fecha inicio (YYYY-MM-DD)
            fecha_fin: Fecha fin (YYYY-MM-DD)
            
        Returns:
            Dict con estructura de datos
        """
        # Validación
        if not validar_fecha(fecha_inicio) or not validar_fecha(fecha_fin):
            raise ValueError("Formato de fecha inválido")
        
        # Lógica principal
        ...
```

### Template: Router Modularizado

```python
# backend/routers/mi_modulo/__init__.py
"""Router principal del módulo."""
from fastapi import APIRouter
from .consultas import router as consultas_router
from .operaciones import router as operaciones_router

router = APIRouter(
    prefix="/api/v1/mi-modulo",
    tags=["mi-modulo"]
)

router.include_router(consultas_router)
router.include_router(operaciones_router)
```

```python
# backend/routers/mi_modulo/consultas.py
"""Endpoints de consulta (GET)."""
from fastapi import APIRouter, Query
from backend.services.mi_modulo import MiModuloService

router = APIRouter()

@router.get("/lista")
async def get_lista(
    fecha_inicio: str = Query(...),
    fecha_fin: str = Query(...),
    username: str = Query(...),
    password: str = Query(...)
):
    """Obtiene lista de items."""
    service = MiModuloService(username=username, password=password)
    return service.get_datos_principales(fecha_inicio, fecha_fin)
```

```python
# backend/routers/mi_modulo/operaciones.py
"""Endpoints de operaciones (POST, PUT, DELETE)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.mi_modulo import MiModuloService

router = APIRouter()

class CreateRequest(BaseModel):
    nombre: str
    cantidad: float

@router.post("/crear")
async def crear_item(
    request: CreateRequest,
    username: str,
    password: str
):
    """Crea un nuevo item."""
    try:
        service = MiModuloService(username=username, password=password)
        return service.crear_item(request.nombre, request.cantidad)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

---

## 🚫 Anti-Patrones a Evitar

### ❌ NO hacer:

1. **Módulos con dependencias circulares**
```python
# helpers.py importa de service.py
# service.py importa de helpers.py
# ❌ MAL
```

2. **Helpers con estado mutable**
```python
# helpers.py
cached_data = {}  # ❌ Estado global

def get_data():
    return cached_data  # ❌ No usar globals
```

3. **Funciones genéricas en módulos específicos**
```python
# backend/services/compras/helpers.py
def format_currency(amount):  # ❌ Debería estar en utils/
    ...
```

4. **Extraer prematuramente**
```python
# No modularizar hasta que el archivo tenga > 800 líneas
# o funciones con > 100 líneas
```

5. **Módulos sin cohesión**
```python
# backend/utils/mixed.py
def calcular_rendimiento():  # ❌ Función específica de rendimiento
def format_date():           # ✅ Función genérica
def procesar_compra():       # ❌ Función específica de compras
```

### ✅ SÍ hacer:

1. **Imports explícitos**
```python
from .helpers import validar_fecha, normalizar_nombre
# No usar: from .helpers import *
```

2. **Funciones puras cuando sea posible**
```python
def calcular_total(items: List[Dict]) -> float:
    """Función pura: mismo input → mismo output."""
    return sum(item['amount'] for item in items)
```

3. **Type hints siempre**
```python
def procesar_datos(
    data: List[Dict],
    filtro: Optional[str] = None
) -> Dict[str, Any]:
    ...
```

4. **Docstrings en funciones públicas**
```python
def get_dashboard_data(fecha_inicio: str, fecha_fin: str) -> Dict:
    """
    Obtiene datos consolidados del dashboard.
    
    Args:
        fecha_inicio: Fecha inicio en formato YYYY-MM-DD
        fecha_fin: Fecha fin en formato YYYY-MM-DD
        
    Returns:
        Dict con estructura: {
            'kpis': {...},
            'grafico': {...}
        }
        
    Raises:
        ValueError: Si las fechas son inválidas
    """
    ...
```

---

## 📊 Métricas de Éxito

### Indicadores de buena modularización:

- ✅ Ningún archivo service > 800 líneas
- ✅ Ningún archivo router > 300 líneas
- ✅ Ninguna función > 100 líneas
- ✅ Código reutilizable en `utils/` o módulos compartidos
- ✅ Fácil localizar funcionalidad (nombres descriptivos)
- ✅ Tests unitarios simples de escribir
- ✅ Cambios no afectan múltiples módulos

### Indicadores de modularización excesiva:

- ⚠️ Archivos con < 50 líneas y una sola función
- ⚠️ Más de 3 niveles de carpetas anidadas
- ⚠️ Imports que recorren más de 2 niveles
- ⚠️ Código duplicado entre módulos

---

## 🔄 Proceso de Migración

### Paso a Paso:

1. **Análisis** (30 min)
   - Identificar archivo a modularizar
   - Leer código completo
   - Identificar responsabilidades separables
   - Dibujar estructura propuesta

2. **Planificación** (15 min)
   - Crear estructura de carpetas
   - Definir nombres de archivos
   - Planificar orden de extracción

3. **Implementación** (2-4 horas)
   - Crear carpeta `modulo/`
   - Crear `__init__.py`
   - Extraer constantes → `constants.py`
   - Extraer helpers → `helpers.py`
   - Extraer calculators → `calculators.py`
   - Refactorizar service principal → `service.py`
   - Actualizar imports en archivos dependientes

4. **Testing** (30 min)
   - Ejecutar servidor: `python -m uvicorn backend.main:app`
   - Probar endpoints en Postman/navegador
   - Verificar logs sin errores
   - Probar frontend conectado

5. **Documentación** (15 min)
   - Actualizar este documento si es necesario
   - Documentar cambios en CHANGELOG
   - Comentar PR con resumen de cambios

---

## 📚 Recursos y Referencias

- **Guía de desarrollo:** `.agent/workflows/DEVELOPER-GUIDE.md`
- **Estructura del proyecto:** `.agent/workflows/project-structure.md`
- **Guía de modularización frontend:** `.agent/workflows/MODULARIZATION_GUIDE.md`

### Módulos de Referencia

**Bien modularizados:**
- `backend/services/comercial_service.py` (477 líneas)
- `backend/services/permissions_service.py` (315 líneas)
- `pages/11_Relacion_Comercial.py` (frontend bien modularizado)

**Necesitan modularización:**
- `backend/services/tuneles_service.py` (2252 líneas)
- `backend/services/flujo_caja_service.py` (1551 líneas)
- `backend/services/rendimiento_service.py` (1306 líneas)

---

## 🎓 Ejemplo Completo

Ver ejemplo detallado de modularización de `rendimiento_service.py` en la sección **Estructura de Modularización > Caso 2**.

---

**Última actualización:** 9 de Enero 2026  
**Mantenido por:** Equipo de Desarrollo Rio Futuro  
**Versión:** 1.0
