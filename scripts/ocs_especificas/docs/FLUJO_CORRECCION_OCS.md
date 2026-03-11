# 📋 FLUJO DE CORRECCIÓN DE ÓRDENES DE COMPRA EN ODOO

## 🎯 Objetivo
Protocolo estandarizado para corregir errores en Órdenes de Compra (Purchase Orders) que ya tienen recepciones procesadas, garantizando la integridad contable y operativa.

---

## 📊 RESUMEN EJECUTIVO

### OCs Corregidas (8 totales)
| OC | Corrección | Impacto $ |
|---|---|---|
| **OC12288** | Precio $0→$2.00 USD | $1,182.60 |
| **OC11401** | Precio $6.50→$1.60 USD + eliminación factura borrador | $9,017.60 |
| **OC12902** | Precio $3,080→$3,085 CLP | $17,922,554 |
| **OC09581** | Cantidad 103→746.65 kg | $2,043.30 USD |
| **OC12755** | Precio $0→$2,000 CLP + cantidad 110→138.480 | $329,582 CLP |
| **OC13491** | Precio $3,400→$3,300 + cantidad 5,015→4,975.760 | $19,539,810 CLP |
| **OC13530** | Precio $3,400→$3,300 + cantidad 4,730→4,566.060 | $17,930,918 CLP |
| **OC13596** | Precio $3,400→$3,300 + cantidad 3,125→3,104.160 | $12,190,036 CLP |

### Estadísticas Globales
- ✅ **9 líneas de compra** actualizadas
- ✅ **13 recepciones** (pickings) procesadas
- ✅ **27 movimientos** de inventario validados
- ✅ **4 OCs facturadas** (OC09581, OC13491, OC13530, OC13596)
- ✅ **4 OCs pendientes** de facturar

---

## 🔄 FLUJO DE CORRECCIÓN (5 FASES)

### FASE 1️⃣: ANÁLISIS E INVESTIGACIÓN
**Objetivo**: Entender el alcance completo del error y su impacto

#### Pasos:
1. **Identificar el error reportado**
   - Revisar qué está mal: precio, cantidad, moneda, etc.
   - Obtener valor correcto confirmado

2. **Buscar la Orden de Compra**
   ```python
   oc = models.execute_kw(db, uid, password, 'purchase.order', 'search_read',
       [[['name', '=', 'OC12288']]],
       {'fields': ['id', 'state', 'currency_id', 'amount_total', 'invoice_status']}
   )
   ```

3. **Analizar líneas de compra** (purchase.order.line)
   - Cantidad pedida vs recibida vs facturada
   - Precio unitario actual
   - Subtotal de cada línea

4. **Verificar recepciones** (stock.picking)
   - Estado de las recepciones (done/draft/cancel)
   - Fecha de procesamiento

5. **Revisar movimientos de inventario** (stock.move)
   - Cantidades esperadas vs realizadas
   - Estado de cada movimiento (done/cancel)

6. **Buscar capas de valoración** (stock.valuation.layer)
   - Búsqueda por descripción (ej: 'OC12288')
   - Valor en inventario afectado
   - Costo unitario registrado

7. **Verificar facturas** (account.move)
   - Facturas en borrador (draft) que puedan bloquear corrección
   - Facturas confirmadas (posted)
   - Asientos contables relacionados

#### ⚠️ Alertas Críticas:
- **Facturas en borrador**: DEBEN eliminarse antes de corregir
- **Facturas confirmadas**: Requieren nota de crédito, NO se puede corregir directamente
- **Recepciones canceladas**: Verificar si afectan la corrección

---

### FASE 2️⃣: VALIDACIÓN DE PREREQUISITOS
**Objetivo**: Asegurar que la corrección es posible sin romper integridad

#### Checklist de Validación:
- [ ] OC en estado 'purchase' (confirmada)
- [ ] No hay facturas confirmadas (posted) relacionadas*
- [ ] Facturas en borrador identificadas para eliminación
- [ ] Recepciones procesadas (done) identificadas
- [ ] Cantidades recibidas confirmadas
- [ ] Nuevo valor (precio/cantidad) validado con usuario

*Si hay facturas confirmadas, el proceso cambia: usar notas de crédito y nueva factura

#### Decisiones:
1. **Si hay factura borrador**: Eliminarla antes de corregir
2. **Si hay factura confirmada**: Cancelar corrección o usar nota de crédito
3. **Si moneda incorrecta**: Corregir moneda ANTES de precio

---

### FASE 3️⃣: DISEÑO DE LA CORRECCIÓN
**Objetivo**: Planificar exactamente qué registros se actualizarán

#### Elementos a Corregir:

**A. Línea de Compra** (purchase.order.line)
```python
{
    'product_qty': CANTIDAD_NUEVA,      # Si aplica
    'price_unit': PRECIO_NUEVO,         # Si aplica
    'currency_id': MONEDA_ID            # Si aplica
}
```

**B. Movimientos de Inventario** (stock.move)
- ⚠️ **PRECAUCIÓN**: Solo si no están 'done'
- Generalmente Odoo los ajusta automáticamente

**C. Capas de Valoración** (stock.valuation.layer)
- ⚠️ **PRECAUCIÓN**: Modificar solo si es absolutamente necesario
- Pueden requerir ajustes contables manuales

**D. Orden de Compra** (purchase.order)
- Moneda (currency_id) si es necesario
- El total se recalcula automáticamente

---

### FASE 4️⃣: EJECUCIÓN
**Objetivo**: Aplicar los cambios en el orden correcto

#### Secuencia de Ejecución:

**Paso 1: Eliminar Facturas Borrador** (si existen)
```python
# Ejemplo: OC11401 tenía factura ID 307678 en borrador
models.execute_kw(db, uid, password, 'account.move', 'unlink', [[307678]])
```

**Paso 2: Corregir Moneda de OC** (si aplica)
```python
# Ejemplo: OC12902 USD→CLP
models.execute_kw(db, uid, password, 'purchase.order', 'write',
    [[oc_id], {'currency_id': CLP_ID}]
)
```

**Paso 3: Corregir Líneas de Compra**
```python
# Actualizar precio y/o cantidad
models.execute_kw(db, uid, password, 'purchase.order.line', 'write',
    [[linea_id], {
        'product_qty': cantidad_nueva,
        'price_unit': precio_nuevo
    }]
)
```

**Paso 4: Verificación Inmediata**
- Re-leer registros actualizados
- Confirmar valores correctos
- Validar subtotales y totales

#### ⚠️ Manejo de Errores:
```python
try:
    result = models.execute_kw(...)
    if result:
        print("✅ ACTUALIZADO")
    else:
        print("❌ ERROR")
except Exception as e:
    print(f"❌ EXCEPCIÓN: {e}")
    # NO continuar si hay error
```

---

### FASE 5️⃣: VERIFICACIÓN Y LOGGING
**Objetivo**: Confirmar que todo quedó correcto y documentar

#### Verificaciones Post-Corrección:

**1. Verificar Orden de Compra**
```python
oc_final = models.execute_kw(db, uid, password, 'purchase.order', 'read',
    [[oc_id]], {'fields': ['amount_total', 'currency_id']}
)
# Validar que total sea el esperado
```

**2. Verificar Líneas**
```python
lineas_final = models.execute_kw(db, uid, password, 'purchase.order.line', 'search_read',
    [[['order_id', '=', oc_id]]],
    {'fields': ['product_qty', 'price_unit', 'price_subtotal']}
)
# Validar cantidades y precios
```

**3. Verificar Coherencia**
- Cantidad pedida vs recibida (debe tener sentido)
- Precio unitario correcto
- Subtotales calculados correctamente
- Total de OC = suma de subtotales + impuestos

**4. Logging Obligatorio**
```python
log = {
    'oc': 'OC12288',
    'fecha_ejecucion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    'cambios': [
        {
            'modelo': 'purchase.order.line',
            'id': 20111,
            'campo': 'price_unit',
            'antes': 0.0,
            'despues': 2.0
        }
    ],
    'total_antes': 0.00,
    'total_despues': 1182.60
}

# Guardar JSON
with open(f'oc_ejecucion_{timestamp}.json', 'w') as f:
    json.dump(log, f, indent=2, ensure_ascii=False)
```

---

## 🎓 LECCIONES APRENDIDAS

### ✅ Buenas Prácticas:
1. **Siempre analizar primero** - Nunca corregir sin análisis completo
2. **Eliminar facturas borrador** - Antes de cualquier corrección
3. **Corregir moneda primero** - Luego precio/cantidad
4. **Validación de producto** - Verificar currency_id del producto
5. **Logging exhaustivo** - Documentar TODO (JSON + console)
6. **Verificación inmediata** - Re-leer datos después de cada write
7. **Un paso a la vez** - No corregir múltiples OCs simultáneamente sin validar

### ❌ Errores a Evitar:
1. **NO** corregir OCs con facturas confirmadas sin nota de crédito
2. **NO** cambiar moneda y precio en el mismo write si hay validación del producto
3. **NO** asumir que los valores están bien - siempre verificar
4. **NO** olvidar actualizar stock.move y stock.valuation.layer (corrección en cadena)
5. **NO** continuar si hay excepciones - investigar primero
6. **NO** olvidar verificar el estado (draft/done/cancel)
7. **NO** buscar capas de valoración solo por 'description' - usar 'stock_move_id'
8. **NO** asumir que Odoo propagará automáticamente los cambios de precio

### 🔍 Puntos de Atención:
- **Productos con currency_id**: Validar compatibilidad antes de cambiar moneda de línea
- **Recepciones parciales**: Cantidad recibida puede ser diferente a pedida (normal)
- **Movimientos cancelados**: No afectan inventario, ignorar en cálculos
- **Facturas posted**: Requieren proceso diferente (nota crédito + nueva factura)

---

## 🛠️ HERRAMIENTAS UTILIZADAS

### Modelos de Odoo:
- `purchase.order` - Orden de compra
- `purchase.order.line` - Líneas de la orden
- `stock.picking` - Recepciones
- `stock.move` - Movimientos de inventario
- `stock.valuation.layer` - Capas de valoración (contabilidad de inventario)
- `account.move` - Facturas y asientos contables
- `account.move.line` - Líneas de facturas
- `res.currency` - Monedas (CLP, USD)
- `product.product` - Productos (currency validation)

### Métodos XML-RPC:
- `search_read` - Buscar y leer en un solo paso
- `read` - Leer registros por IDs
- `write` - Actualizar registros
- `unlink` - Eliminar registros (ej: facturas borrador)

---

## 📈 IMPACTO CONTABLE VERIFICADO

### Por Moneda:
**USD**: $12,243.50
- OC12288: $1,182.60
- OC11401: $9,017.60
- OC09581: $2,043.30

**CLP**: $67,912,900
- OC12902: $17,922,554
- OC12755: $329,582
- OC13491: $19,539,810
- OC13530: $17,930,918
- OC13596: $12,190,036

### Estados:
- **4 OCs facturadas**: OC09581, OC13491, OC13530, OC13596
- **4 OCs por facturar**: OC12288, OC11401, OC12902, OC12755

### ⚠️ ACTUALIZACIÓN CRÍTICA - CORRECCIÓN EN CADENA:

**DESCUBRIMIENTO IMPORTANTE**: Los precios NO se propagan automáticamente de purchase.order.line a stock.move y stock.valuation.layer.

**CORRECCIÓN EN CADENA OBLIGATORIA**:
1. ✅ Actualizar **purchase.order.line** (precio/cantidad)
2. ✅ Actualizar **stock.move** (price_unit) - MANUAL
3. ✅ Actualizar **stock.valuation.layer** (unit_cost y value) - MANUAL

**Buscar capas de valoración**:
- ❌ NO buscar solo por 'description' (no siempre funciona)
- ✅ Buscar por 'stock_move_id' (método confiable)

**Impacto contable real**:
- Las capas de valoración DEBEN actualizarse para reflejar el costo correcto en inventario
- Si no se actualizan, el inventario tendrá valoración incorrecta
- Las facturas futuras se generan correctamente, pero el valor en libros del inventario queda mal

---

## 📝 CONCLUSIÓN

✅ **Todas las OCs fueron corregidas exitosamente**

✅ **Integridad de datos mantenida**:
- Cantidades coinciden con recepciones reales
- Precios reflejan valores correctos
- Monedas correctas en cada OC
- Subtotales recalculados automáticamente

✅ **Proceso documentado y replicable**

✅ **Logs generados para auditoría**:
- oc12288_ejecucion_20260311_103757.json
- oc11401_ejecucion_20260311_105307.json
- correccion_3_ocs_20260311_110953.json (OC12902, OC09581, OC12363)
- oc09581_cantidad_ejecucion_20260311_111735.json
- correccion_4_ocs_20260311_113000.json (OC12755, OC13491, OC13530, OC13596)
- REPORTE_COMPLETO_OCs_20260311_115639.json

---

**Fecha de creación**: 11 de Marzo, 2026
**Autor**: Sistema de corrección automática de OCs
**Versión**: 1.0
