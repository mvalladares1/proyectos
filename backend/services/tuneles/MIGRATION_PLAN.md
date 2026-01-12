# Plan de Modularización - Túneles Service

## Estado Actual
- **Archivo:** `tuneles_service.py`
- **Líneas:** 2252
- **Funciones:** 18

## Estructura Modularizada

```
backend/services/tuneles/
├── __init__.py          ✅ CREADO - Exporta TunelesService
├── constants.py         ✅ CREADO - Configuración túneles, productos, ubicaciones
├── helpers.py           ✅ CREADO - Búsqueda/creación lotes y packages (batch)
├── service.py           🔄 EN PROGRESO - Clase principal orquestadora
└── MIGRATION_PLAN.md    📝 Este archivo
```

## Resumen de Extracción

### constants.py (68 líneas)
- `TUNELES_CONFIG` - Config de 4 túneles (TE1, TE2, TE3, VLK)
- `PRODUCTOS_TRANSFORMACION` - Mapeo fresco→congelado
- `PRODUCTO_ELECTRICIDAD_ID`, `UOM_DOLARES_KG_ID`
- `UBICACION_VIRTUAL_CONGELADO_ID`, `UBICACION_VIRTUAL_PROCESOS_ID`

### helpers.py (150 líneas)
**Funciones extraídas:**
- `buscar_o_crear_lotes_batch()` - Optimización batch para lotes
- `buscar_o_crear_packages_batch()` - Optimización batch para packages
- `buscar_o_crear_lote()` - Búsqueda/creación individual

### service.py (~2000 líneas)
**Métodos públicos (mantener en clase):**
- `get_tuneles_disponibles()` 
- `validar_pallets_batch()` - Validación optimizada con 2 llamadas
- `validar_pallet()` - Wrapper de batch para 1 pallet
- `verificar_pendientes()` - Estado de recepciones pendientes
- `completar_pendientes()` - Marca pendientes como completos
- `reset_estado_pendientes()` - Debug: resetea timestamps
- `obtener_detalle_pendientes()` - Detalle completo con stock
- `agregar_componentes_disponibles()` - Agrega pallets ahora disponibles
- `listar_ordenes_recientes()` - Lista MOs de túneles
- `check_pallets_duplicados()` - Verifica duplicados en otras MOs
- `crear_orden_fabricacion()` - Creación completa de MO

**Métodos privados (mantener en clase - usan self.odoo extensivamente):**
- `_crear_componentes()` - Crea move_raw_ids + electricidad
- `_crear_subproductos()` - Crea move_finished_ids con lotes -C

**Imports necesarios:**
```python
from .constants import (
    TUNELES_CONFIG, PRODUCTOS_TRANSFORMACION,
    PRODUCTO_ELECTRICIDAD_ID, UOM_DOLARES_KG_ID,
    UBICACION_VIRTUAL_CONGELADO_ID, UBICACION_VIRTUAL_PROCESOS_ID
)
from .helpers import (
    buscar_o_crear_lotes_batch,
    buscar_o_crear_packages_batch,
    buscar_o_crear_lote
)
```

## Decisiones de Diseño

### ✅ Modularizar
- **Constantes:** Fácil extracción, cero dependencias
- **Helpers batch:** Funciones puras, reutilizables

### ❌ NO Modularizar (por ahora)
- **Validadores:** Dependen mucho de `self.odoo` y lógica compleja entrelazada
- **Creadores:** Métodos privados con mucha interacción con la clase
- **Lógica de negocio principal:** Crear_orden_fabricacion() muy acoplada

## Reducción de Líneas

| Componente | Antes | Después | Reducción |
|-----------|-------|---------|-----------|
| tuneles_service.py | 2252 | ~2030 | 222 líneas (10%) |
| Nuevos módulos | 0 | 218 | +218 líneas |
| **TOTAL** | 2252 | 2248 | -4 líneas netas |

**Nota:** La reducción neta es mínima, pero la **organización** mejora significativamente.

## Beneficios

✅ **Constantes centralizadas:** Fácil encontrar configuración de túneles  
✅ **Helpers reutilizables:** `buscar_o_crear_lotes_batch` puede usarse en otros servicios  
✅ **Imports explícitos:** Claridad en dependencias  
✅ **Preparado para futuras extracciones:** Si validators crece, ya tiene su lugar

## Próximos Pasos (Futuro)

Si el service sigue creciendo (>2500 líneas), considerar:
1. **validators.py** - Extraer toda la lógica de validación de pallets
2. **creators.py** - Extraer `_crear_componentes` y `_crear_subproductos`
3. **monitoring.py** - Extraer funciones de monitoreo y listado

## Actualización de Imports

### Archivos a actualizar:
- `backend/routers/automatizaciones.py`
  ```python
  # Antes:
  from backend.services.tuneles_service import TunelesService
  
  # Después:
  from backend.services.tuneles import TunelesService
  ```

## Testing

Verificar después de migración:
```bash
# Endpoint de túneles
curl http://localhost:8000/api/v1/automatizaciones/tuneles

# Validación de pallet
curl http://localhost:8000/api/v1/automatizaciones/validar-pallet?pallet=PACK0010337

# Crear MO
curl -X POST http://localhost:8000/api/v1/automatizaciones/crear-mo
```

---

**Fecha:** 12 de Enero 2026  
**Status:** ✅ Helpers y Constants extraídos  
**Pendiente:** Migrar service.py principal
