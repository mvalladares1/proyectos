# 📚 SISTEMA DE CORRECCIÓN DE ÓRDENES DE COMPRA

Sistema estandarizado para corregir errores en Órdenes de Compra (Purchase Orders) en Odoo ERP, garantizando integridad contable completa mediante corrección en cadena.

---

## 🎯 ¿Qué hace este sistema?

Corrige errores en OCs que ya tienen recepciones procesadas, actualizando **toda la cadena contable**:

```
purchase.order        (Orden de Compra)
       ↓
purchase.order.line   (Líneas de productos)
       ↓
stock.move           (Movimientos de inventario)
       ↓
stock.valuation.layer (Valoración contable)
       ↓
account.move         (Asientos/Facturas)
```

---

## 📖 DOCUMENTACIÓN

| Documento | Descripción | Cuándo usarlo |
|-----------|-------------|---------------|
| **[GUIA_RAPIDA.md](GUIA_RAPIDA.md)** | Guía de uso con ejemplos | ⭐ Empezar aquí |
| **[FLUJO_CORRECCION_OCS.md](FLUJO_CORRECCION_OCS.md)** | Documentación completa del flujo | Para entender el proceso en detalle |

---

## 🚀 INICIO RÁPIDO

### 1. Copiar Templates
```bash
# Análisis
cp TEMPLATE_1_analizar_oc.py analizar_oc12345.py

# Corrección
cp TEMPLATE_2_corregir_oc_cadena.py EJECUTAR_corregir_oc12345.py
```

### 2. Configurar Variables
Editar en `analizar_oc12345.py`:
```python
OC_NAME = 'OC12345'
PRECIO_CORRECTO = 2000.0  # o None
CANTIDAD_CORRECTA = 138.48  # o None
```

### 3. Ejecutar Análisis
```bash
python analizar_oc12345.py
```

### 4. Configurar Corrección
Editar en `EJECUTAR_corregir_oc12345.py` con datos del análisis:
```python
OC_NAME = 'OC12345'
CORRECCIONES = {
    'lineas': [
        {
            'linea_id': 20854,        # ⬅️ Del análisis
            'precio_nuevo': 2000.0,
            'cantidad_nueva': 138.48,
            'moves_ids': [163847]     # ⬅️ Del análisis
        }
    ],
    'facturas_borrador_eliminar': []
}
```

### 5. Ejecutar Corrección
```bash
python EJECUTAR_corregir_oc12345.py
```

---

## 📂 ARCHIVOS DEL SISTEMA

### Templates (NO modificar directamente)
- `TEMPLATE_1_analizar_oc.py` - Template para análisis
- `TEMPLATE_2_corregir_oc_cadena.py` - Template para corrección

### Utilidades
- `verificar_propagacion_precios.py` - Verifica que precios estén correctos en toda la cadena

### Documentación
- `README.md` - Este archivo (índice)
- `GUIA_RAPIDA.md` - Guía de uso con ejemplos
- `FLUJO_CORRECCION_OCS.md` - Documentación técnica completa

---

## ✅ CASOS DE USO SOPORTADOS

| Caso | Soportado | Notas |
|------|-----------|-------|
| Corregir precio | ✅ | Con corrección en cadena |
| Corregir cantidad | ✅ | Actualiza línea de compra |
| Cambiar moneda | ✅ | Hacer antes de cambiar precio |
| Precio + cantidad | ✅ | Ambos en un solo script |
| Eliminar factura borrador | ✅ | Automático en el flujo |
| Factura confirmada | ❌ | Requiere nota de crédito (proceso manual) |
| Múltiples líneas | ✅ | Configurar array de líneas |
| Múltiples OCs | ⚠️ | Hacer una por una para validar |

---

## 📊 ESTADÍSTICAS DE CORRECCIONES REALIZADAS

**Total OCs corregidas**: 8

| OC | Tipo Corrección | Impacto | Estado |
|----|-----------------|---------|--------|
| OC12288 | Precio | $1,182.60 USD | ✅ |
| OC11401 | Precio + Factura | $9,017.60 USD | ✅ |
| OC12902 | Moneda + Precio | $17,922,554 CLP | ✅ |
| OC09581 | Cantidad | $2,043.30 USD | ✅ |
| OC12755 | Precio + Cantidad | $329,582 CLP | ✅ |
| OC13491 | Precio + Cantidad | $19,539,810 CLP | ✅ |
| OC13530 | Precio + Cantidad | $17,930,918 CLP | ✅ |
| OC13596 | Precio + Cantidad | $12,190,036 CLP | ✅ |

**Logs disponibles**: Todos en formato JSON

---

## 🔑 CONCEPTOS CLAVE

### Corrección en Cadena
**CRÍTICO**: Los cambios en `purchase.order.line` NO se propagan automáticamente.

**Debes actualizar manualmente**:
1. `purchase.order.line` (precio_unit, product_qty)
2. `stock.move` (price_unit) - Solo moves con quantity_done > 0
3. `stock.valuation.layer` (unit_cost, value) - Buscar por stock_move_id

### Búsqueda de Capas de Valoración
```python
# ✅ MÉTODO CONFIABLE
models.execute_kw(..., 'stock.valuation.layer', 'search_read',
    [[['stock_move_id', '=', move_id]]], ...)

# ❌ MÉTODO INCOMPLETO (puede fallar)
models.execute_kw(..., 'stock.valuation.layer', 'search_read',
    [[['description', 'ilike', oc_name]]], ...)
```

### Eliminación de Facturas
- **Borrador (draft)**: Se puede eliminar con `unlink()`
- **Confirmada (posted)**: NO usar este sistema, requiere nota de crédito

---

## ⚠️ PREREQUISITOS

### Antes de corregir:
- [ ] OC en estado 'purchase' (confirmada)
- [ ] Sin facturas confirmadas relacionadas
- [ ] Valor correcto confirmado con usuario
- [ ] Análisis completo ejecutado

### Validaciones automáticas:
- Estado de OC
- Facturas borrador (se eliminan automáticamente)
- Facturas confirmadas (bloquea ejecución)
- Recepciones procesadas

---

## 🎓 APRENDIZAJES DOCUMENTADOS

### ✅ Qué funciona bien:
1. Análisis exhaustivo antes de corregir
2. Corrección en cadena (line → move → layer)
3. Búsqueda de capas por stock_move_id
4. Logging detallado en JSON
5. Verificación inmediata post-corrección
6. Templates reutilizables

### ❌ Qué NO hacer:
1. Corregir sin análisis previo
2. Asumir propagación automática
3. Cambiar moneda y precio simultáneamente
4. Ignorar facturas borrador
5. Modificar OCs con facturas confirmadas
6. Buscar capas solo por description

### 🔍 Descubrimientos importantes:
1. **Odoo NO propaga precios automáticamente** de purchase.order.line a stock.move
2. **Capas de valoración** deben buscarse por stock_move_id, no por description
3. **Moneda del producto** puede bloquear cambios de moneda en línea
4. **Movimientos cancelados** (quantity_done=0) no afectan contabilidad
5. **Facturas borrador** bloquean correcciones de precio

---

## 📝 LOGS Y TRAZABILIDAD

Cada ejecución genera un archivo JSON:
```
ocXXXXX_ejecucion_YYYYMMDD_HHMMSS.json
```

**Contenido**:
- Fecha y hora de ejecución
- Todos los cambios realizados (por tipo y ID)
- Valores antes/después
- Total de OC antes/después

**Ejemplo**:
```json
{
  "oc": "OC12755",
  "fecha_ejecucion": "2026-03-11 11:30:00",
  "cambios": [
    {
      "tipo": "purchase.order.line",
      "id": 20854,
      "precio_antes": 0.0,
      "precio_despues": 2000.0
    },
    {
      "tipo": "stock.move",
      "id": 163847,
      "precio_antes": 0.0,
      "precio_despues": 2000.0
    }
  ],
  "total_antes": 0.0,
  "total_despues": 329582.0
}
```

---

## 🔄 FLUJO VISUAL

```
┌─────────────────────────┐
│  1. ANALIZAR            │
│  TEMPLATE_1_analizar    │
│  - Identificar error    │
│  - Ver facturas         │
│  - Obtener IDs          │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│  2. CONFIGURAR          │
│  TEMPLATE_2_corregir    │
│  - Copiar IDs           │
│  - Configurar valores   │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│  3. EJECUTAR            │
│  - Eliminar facturas    │
│  - Actualizar líneas    │
│  - Actualizar moves     │
│  - Actualizar layers    │
└───────────┬─────────────┘
            │
            ↓
┌─────────────────────────┐
│  4. VERIFICAR           │
│  - Total correcto       │
│  - Precios en cadena    │
│  - Log generado         │
└─────────────────────────┘
```

---

## 🆘 SOPORTE Y TROUBLESHOOTING

### Error común: "Moneda de compra no es correcta"
**Solución**: Cambiar moneda en paso separado, antes de precio

### Error común: "No se encuentran capas de valoración"
**Solución**: Verificar que se buscan por stock_move_id en el template

### Error común: Total OC no coincide
**Solución**: Verificar que purchase.order.line tenga precio correcto

### Para casos no cubiertos:
1. Revisar [FLUJO_CORRECCION_OCS.md](FLUJO_CORRECCION_OCS.md)
2. Revisar logs de correcciones exitosas similares
3. Ejecutar análisis completo y revisar cada paso

---

## 🔐 SEGURIDAD

### Credenciales:
- Nunca compartir password fuera del equipo
- Rotar password regularmente
- Templates incluyen credenciales hardcoded (mantener en servidor seguro)

### Backups:
- Odoo mantiene histórico de cambios
- Logs JSON permiten auditoría
- Se puede revertir manualmente si es necesario

---

## 📅 MANTENIMIENTO

### Actualizar templates:
1. Modificar TEMPLATE_*.py según necesidad
2. Actualizar documentación (GUIA_RAPIDA.md, FLUJO_CORRECCION_OCS.md)
3. Probar con OC de prueba antes de usar en producción

### Agregar nueva funcionalidad:
1. Documentar en FLUJO_CORRECCION_OCS.md
2. Actualizar GUIA_RAPIDA.md con ejemplo
3. Modificar templates si aplica
4. Actualizar este README

---

## ✨ CARACTERÍSTICAS

- ✅ **Automatización completa** de corrección en cadena
- ✅ **Templates reutilizables** para cualquier OC
- ✅ **Validaciones automáticas** (estado, facturas, etc.)
- ✅ **Logging exhaustivo** en JSON
- ✅ **Verificación post-corrección** automática
- ✅ **Documentación completa** con ejemplos
- ✅ **Casos de uso reales** documentados
- ✅ **8 OCs corregidas** exitosamente

---

## 📊 MODELOS DE ODOO UTILIZADOS

| Modelo | Uso | Campos Clave |
|--------|-----|--------------|
| `purchase.order` | Orden de compra | id, state, currency_id, amount_total |
| `purchase.order.line` | Líneas de productos | id, price_unit, product_qty |
| `stock.picking` | Recepciones | id, name, state, origin |
| `stock.move` | Movimientos inventario | id, price_unit, quantity_done |
| `stock.valuation.layer` | Valoración contable | id, unit_cost, value, stock_move_id |
| `account.move` | Facturas/Asientos | id, state, amount_total |
| `res.currency` | Monedas | id, name (CLP=45, USD=2) |

---

## 🎯 PRÓXIMOS PASOS RECOMENDADOS

1. **Leer** [GUIA_RAPIDA.md](GUIA_RAPIDA.md)
2. **Revisar** ejemplos de correcciones exitosas
3. **Copiar** templates para nueva corrección
4. **Ejecutar** análisis antes de cualquier cambio
5. **Documentar** nuevos casos de uso encontrados

---

**Versión**: 2.0  
**Última actualización**: 11 de Marzo, 2026  
**Autor**: AGRICOLA RIO FUTURO Spa  
**Contacto**: mvalladares@riofuturo.cl
