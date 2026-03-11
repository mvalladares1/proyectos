# 🚀 GUÍA RÁPIDA: Corrección de Órdenes de Compra

## 📋 Checklist Pre-Corrección

- [ ] Identificar OC con error
- [ ] Obtener valor correcto confirmado (precio/cantidad)
- [ ] Verificar que OC esté en estado 'purchase'
- [ ] Verificar facturas (borrador vs confirmadas)
- [ ] Validar moneda correcta

---

## 🔄 FLUJO ESTÁNDAR (3 PASOS)

### PASO 1: ANALIZAR
```bash
# Copiar TEMPLATE_1_analizar_oc.py → analizar_ocXXXXX.py
# Editar variables:
OC_NAME = 'OC12345'
PRECIO_CORRECTO = 2000.0  # o None si no aplica
CANTIDAD_CORRECTA = 138.48  # o None si no aplica

# Ejecutar
python analizar_ocXXXXX.py
```

**Revisar output:**
- ✅ Estado de OC (debe ser 'purchase')
- ✅ Facturas borrador (anotar IDs para eliminar)
- ⛔ Facturas confirmadas (NO CONTINUAR)
- ✅ IDs de líneas de compra (purchase.order.line)
- ✅ IDs de movimientos (stock.move) con cantidad > 0
- ✅ Verificar capas de valoración

---

### PASO 2: CONFIGURAR CORRECCIÓN
```bash
# Copiar TEMPLATE_2_corregir_oc_cadena.py → EJECUTAR_corregir_ocXXXXX.py
```

**Editar configuración:**

```python
OC_NAME = 'OC12345'

CORRECCIONES = {
    'moneda_id': None,  # o 45 para CLP, 2 para USD
    'lineas': [
        {
            'linea_id': 20854,  # ⬅️ Del análisis
            'precio_nuevo': 2000.0,  # ⬅️ Precio correcto
            'cantidad_nueva': 138.48,  # ⬅️ Cantidad correcta
            'moves_ids': [163847]  # ⬅️ Del análisis, solo moves con quantity_done > 0
        }
    ],
    'facturas_borrador_eliminar': [307678]  # ⬅️ Del análisis
}
```

---

### PASO 3: EJECUTAR Y VERIFICAR
```bash
python EJECUTAR_corregir_ocXXXXX.py
```

**Verificar output:**
- ✅ Facturas borrador eliminadas
- ✅ Líneas de compra actualizadas
- ✅ Stock.move actualizados
- ✅ Stock.valuation.layer actualizados
- ✅ Total de OC correcto
- ✅ Log JSON generado

---

## 📖 EJEMPLOS REALES

### Ejemplo 1: Solo Precio
**OC12288**: Precio $0 → $2.0 USD

```python
OC_NAME = 'OC12288'
CORRECCIONES = {
    'moneda_id': None,  # Ya está en USD
    'lineas': [
        {
            'linea_id': 20111,
            'precio_nuevo': 2.0,
            'cantidad_nueva': None,  # No se cambia
            'moves_ids': [160742]
        }
    ],
    'facturas_borrador_eliminar': []
}
```

---

### Ejemplo 2: Solo Cantidad
**OC09581**: Cantidad 103 → 746.65 kg

```python
OC_NAME = 'OC09581'
CORRECCIONES = {
    'moneda_id': None,
    'lineas': [
        {
            'linea_id': 16048,
            'precio_nuevo': None,  # No se cambia
            'cantidad_nueva': 746.65,
            'moves_ids': []  # Cantidad no requiere actualizar moves
        }
    ],
    'facturas_borrador_eliminar': []
}
```

---

### Ejemplo 3: Precio + Cantidad
**OC12755**: Precio $0 → $2,000 + Cantidad 110 → 138.48

```python
OC_NAME = 'OC12755'
CORRECCIONES = {
    'moneda_id': None,
    'lineas': [
        {
            'linea_id': 20854,
            'precio_nuevo': 2000.0,
            'cantidad_nueva': 138.48,
            'moves_ids': [163847]  # Solo movimientos con quantity_done > 0
        }
    ],
    'facturas_borrador_eliminar': []
}
```

---

### Ejemplo 4: Cambio de Moneda + Precio
**OC12902**: Primero USD→CLP, luego precio $3,080 → $3,085

**IMPORTANTE**: Hacer en 2 pasos separados:

**Paso 4a: Cambiar moneda**
```python
OC_NAME = 'OC12902'
CORRECCIONES = {
    'moneda_id': 45,  # CLP
    'lineas': [
        {
            'linea_id': 21140,
            'precio_nuevo': None,  # NO cambiar precio aún
            'cantidad_nueva': None,
            'moves_ids': []
        }
    ],
    'facturas_borrador_eliminar': []
}
```

**Paso 4b: Cambiar precio** (ejecutar script separado)
```python
OC_NAME = 'OC12902'
CORRECCIONES = {
    'moneda_id': None,  # Ya está en CLP
    'lineas': [
        {
            'linea_id': 21140,
            'precio_nuevo': 3085.0,
            'cantidad_nueva': None,
            'moves_ids': [166160]
        }
    ],
    'facturas_borrador_eliminar': []
}
```

---

### Ejemplo 5: Con Eliminación de Factura Borrador
**OC11401**: Eliminar factura + Precio $6.5 → $1.6

```python
OC_NAME = 'OC11401'
CORRECCIONES = {
    'moneda_id': None,
    'lineas': [
        {
            'linea_id': 18552,
            'precio_nuevo': 1.6,
            'cantidad_nueva': None,
            'moves_ids': [155622]
        }
    ],
    'facturas_borrador_eliminar': [307678]  # ⬅️ Factura en borrador
}
```

---

## ⚠️ CASOS ESPECIALES Y ERRORES COMUNES

### ❌ Error: "La moneda de compra para el producto no es correcta"
**Causa**: El producto tiene currency_id=CLP pero la línea es USD

**Solución**:
1. Primero cambiar moneda de OC y línea
2. Luego cambiar precio en script separado

---

### ❌ Factura Confirmada (posted)
**Solución**: NO usar este flujo

**Proceso alternativo**:
1. Crear nota de crédito para la factura
2. Corregir OC
3. Crear nueva factura con valores correctos

---

### ❌ Movimientos Cancelados con Precio Incorrecto
**No es problema**: Si quantity_done = 0, no afecta

**Acción**: Ignorar, no incluir en `moves_ids`

---

### ❌ No se encuentran capas de valoración
**Causas posibles**:
- Método de costeo diferente
- Valoración en otra ubicación
- Búsqueda por description falla

**Solución**: Buscar por `stock_move_id` (el template lo hace automáticamente)

---

## 📊 VERIFICACIÓN POST-CORRECCIÓN

### Checklist de Verificación:
- [ ] Total OC coincide con esperado
- [ ] Líneas de compra tienen precio/cantidad correctos
- [ ] Stock.move (done) tienen price_unit correcto
- [ ] Stock.valuation.layer tienen unit_cost y value correctos
- [ ] Log JSON generado y guardado
- [ ] No hay errores en output

### Verificar en Odoo UI:
1. Abrir OC en Odoo
2. Verificar tab "Productos": cantidad y precio
3. Verificar tab "Recepciones": estado done
4. Ir a Inventario → Valoración → Buscar por OC
5. Verificar costos unitarios

---

## 🛠️ COMANDOS ÚTILES

### Activar entorno virtual:
```powershell
& "c:\new\RIO FUTURO\DASHBOARD\.venv\Scripts\Activate.ps1"
```

### Ejecutar análisis:
```bash
python proyectos\scripts\ocs_especificas\analizar_ocXXXXX.py
```

### Ejecutar corrección:
```bash
python proyectos\scripts\ocs_especificas\EJECUTAR_corregir_ocXXXXX.py
```

### Verificar propagación:
```bash
python proyectos\scripts\ocs_especificas\verificar_propagacion_precios.py
```

---

## 📁 ESTRUCTURA DE ARCHIVOS

```
ocs_especificas/
├── FLUJO_CORRECCION_OCS.md              # Documentación completa
├── GUIA_RAPIDA.md                       # Este archivo
├── TEMPLATE_1_analizar_oc.py            # Template análisis
├── TEMPLATE_2_corregir_oc_cadena.py     # Template corrección
├── verificar_propagacion_precios.py     # Verificación general
│
├── analizar_ocXXXXX.py                  # Análisis específicos
├── EJECUTAR_corregir_ocXXXXX.py         # Correcciones específicas
│
└── *.json                               # Logs de ejecución
```

---

## 🎓 LECCIONES CLAVE

### 1. SIEMPRE Corrección en Cadena
```
purchase.order.line → stock.move → stock.valuation.layer
```
Los cambios NO se propagan automáticamente.

### 2. Buscar Capas por stock_move_id
```python
# ✅ CORRECTO
layers = models.execute_kw(..., 'stock.valuation.layer', 'search_read',
    [[['stock_move_id', '=', move_id]]], ...)

# ❌ INCOMPLETO (puede no encontrar todas)
layers = models.execute_kw(..., 'stock.valuation.layer', 'search_read',
    [[['description', 'ilike', oc_name]]], ...)
```

### 3. Moneda Antes de Precio
Si hay cambio de moneda:
1. Ejecutar script solo con cambio de moneda
2. Ejecutar segundo script para cambio de precio

### 4. Eliminar Facturas Borrador
Siempre antes de cualquier otra corrección.

### 5. Logging Exhaustivo
Cada ejecución debe generar JSON con todos los cambios.

---

## 📞 SOPORTE

Para dudas o casos especiales:
1. Revisar [FLUJO_CORRECCION_OCS.md](FLUJO_CORRECCION_OCS.md)
2. Revisar logs de ejecuciones exitosas anteriores (*.json)
3. Ejecutar análisis completo antes de cualquier corrección

---

**Última actualización**: 11 de Marzo, 2026  
**Versión**: 2.0 (incluye corrección en cadena)
