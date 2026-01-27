# Validaciones de Movimiento Directo de Pallets

## Sistema de Validaciones Implementado

### � Lógica Dual de Movimiento

El sistema maneja **DOS CASOS** automáticamente:

#### **CASO A: Pallet en Stock Real** (tiene quants)
- El pallet ya fue recepcionado y está físicamente en una ubicación
- Se actualizan directamente los `stock.quant.location_id`
- **Validaciones aplicadas**: Todas las descritas abajo

#### **CASO B: Pallet en Pre-Recepción** (sin quants)
- El pallet está en una recepción pendiente (no validada aún)
- Se actualiza el `location_dest_id` de las líneas en `stock.move.line`
- **Validaciones aplicadas**: Solo globales (no aplican las de quants)
- **Ventaja**: Puedes cambiar el destino ANTES de validar la recepción

**Importante**: La validación de "cantidades reservadas" solo aplica para CASO A (stock real). En CASO B (recepciones) no aplica porque es flujo diferente.

---

### �🔒 Validaciones Globales (Pre-movimiento)

Estas se ejecutan ANTES del loop de pallets para evitar procesamiento innecesario:

1. **Ubicación Destino Existe**
   - Verifica que el `location_dest_id` existe en Odoo
   - Error: "Ubicación destino no existe"

2. **Tipo de Ubicación Válido**
   - Solo permite ubicaciones tipo `internal` o `view`
   - Rechaza: `supplier`, `customer`, `inventory`, `production`, `transit`
   - Error: "No se puede mover a ubicación tipo 'X'"
   - **Razón**: Ubicaciones virtuales no son físicas

3. **Ubicación Activa**
   - Verifica que la ubicación destino esté activa (`active=True`)
   - Error: "Ubicación destino desactivada"

---

### 🔍 Validaciones por Pallet (Solo CASO A - Stock Real)

Se ejecutan solo cuando el pallet tiene quants (stock real):

#### 1. **Paquete Existe**
- Verifica que el código del pallet exista en `stock.quant.package`
- Error: "Paquete no encontrado"

#### 2. **Stock Disponible o Recepción Pendiente**
- **CASO A**: Verifica que el paquete tenga quants con `quantity > 0`
- **CASO B**: Si no hay quants, busca en `stock.move.line` de recepciones pendientes
- Error: "Sin stock disponible y sin recepciones pendientes"
- **Razón**: El pallet debe existir en alguno de los dos estados
 (Solo CASO A)**
- Verifica que ningún quant tenga `reserved_quantity > 0`
- Error: "Tiene X quants con Y kg reservados - liberar primero en Odoo"
- **Razón**: Quants reservados están en pedidos/transferencias activas
- **Solución**: Usuario debe ir a Odoo y liberar/cancelar la reserva
- **Nota**: Esta validación NO aplica para CASO B (recepciones)as
- **Solución**: Usuario debe ir a Odoo y liberar/cancelar la reserva
 (Solo CASO A)
#### 4. **Consistencia de Ubicación Origen**
- Verifica que todos los quants del pallet estén en LA MISMA ubicación
- Error: "Quants en X ubicaciones diferentes (...) - inconsistencia de datos"
- **Razón**: Un pallet no debería estar físicamente en múltiples lugares
- **Causa**: Datos corruptos o proceso manual incorrecto en Odoo

#### 5. **Tipo de Ubicación Origen Válido (Solo CASO A)**
- Verifica que la ubicación origen sea tipo `internal` o `view`
- Error: "Origen es tipo 'X' (no movible directamente)"
- **Razón**: Si está en ubicación virtual, usar flujo estándar de Odoo

#### 6. **Origen ≠ Destino (Solo CASO A)**
- Verifica que origen y destino sean diferentes
- Error: "Ya está en [Ubicación]"
- **Razón**: Evitar operaciones inútiles
- **Nota**: En CASO B no hay origen aún, así que esta validación no aplica

---
 (Solo CASO A)

**Problema**: Si falla al mover el quant #3 de 5, los primeros 2 ya se movieron.

**Solución Implementada**:
```python
try:
    for quant in quants:
        # Guardar estado original
        quants_moved.append({"id": quant_id, "original_location": origen})
        
        # Mover quant
        odoo.execute("stock.quant", "write", [quant_id], {"location_id": destino})
        
except Exception as e:
    # ROLLBACK: Revertir todos los quants ya movidos
    for qm in quants_moved:
        odoo.execute("stock.quant", "write", [qm["id"]], {"location_id": qm["original_location"]})
```

**Garantía**: Si algo falla a mitad del movimiento, el pallet queda en su ubicación original completo.

**Nota**: Para CASO B (recepciones), el rollback no es necesario porque es una sola operación atómica (write masivo de todas las líneas)
**Garantía**: Si algo falla a mitad del movimiento, el pallet queda en su ubicación original completo.

---

### 📝 Validaciones del Sistema de Log

1. **Modelo de Log Existe**
   - Verifica que `x_trasferencias_dashboard_v2` exista antes de intentar crear registro
   - **Comportamiento**: Si no existe, el movimiento es exitoso pero sin log

2. **Log NO Bloquea Movimiento**
   - Si falla el registro en log (permisos, campos faltantes, etc.), el movimiento continúa
   - **Razón**: El log es auditoría, no funcionalidad crítica
   - Se imprime advertencia: `⚠️ Error al registrar log para PACKXXXX`

---
 (Solo CASO A)
**Causa**: Pallet está en un pedido de venta o transferencia pendiente  
**Solución**: 
1. Ir a Odoo → Inventario → Operaciones
2. Buscar la transferencia que contiene el pallet
3. Cancelar o validar la transferencia
4. Reintentar movimiento

**Nota**: SiSin stock disponible y sin recepciones pendientes"
**Causa**: Pallet existe pero no tiene ni quants ni está en recepciones  
**Solución**: 
1. Verificar que el código del pallet sea correcto
2. El pallet puede haber sido consumido/vendido completamente
3. Verificar historial del pallet en Odoo

### Error: "Quants en diferentes ubicaciones" (Solo CASO A)iente (CASO B), este error NO aparecerá - simplemente se actualizará el destino.o → Operaciones
2. Buscar la transferencia que contiene el pallet
3. Cancelar o validar la transferencia
4. Reintentar movimiento

### Error: "Quants en diferentes ubicaciones"
**Causa**: Datos inconsistentes (pallet parcialmente movido manualmente)  
**Solución**:
1. Ir a Odoo → Inventario → Paquetes
2. Buscar el paquete por código
3. Ver los quants (Stock On Hand)
4. Mover manualmente cada quant a la misma ubicación
5. Reintentar

### Error: "No se puede mover a ubicación tipo 'customer'"
**Causa**: Intentando mover a ubicación de cliente/proveedor  
**Solución**: 
1. Usar transferencias de salida/entrada estándar de Odoo
2. El movimiento directo solo funciona entre ubicaciones internas

---

## 📊 Respuesta del API

### Estructura de Respuesta

```json
{
  "success_count": 2,
  "er
      "pallet": "PACK0002345",
      "success": true,
      "message": "✅ Recepción: 2 líneas (123.45 kg) → Camara 0°C REAL [WH/IN/00123]",
      "kg": 123.45,
      "lines_count": 2,
      "type": "reception",
      "pickings": ["WH/IN/00123"],
      "to": "Camara 0°C REAL"
    },
    {ror_count": 1,
  "total_kg": 1234.56,
  "details": [
    {
      "pallet": "PACK0001234",
      "success": true,
      "message": "✅ 3 quants (456.78 kg) → Camara 0°C REAL",
      "kg": 456.78,
      "quants_count": 3,
      "from": "Camara 8 0°C",
      "to": "Camara 0°C REAL"
    },
    {
      "pallet": "PACK0005678",
      "success": false,
      "message": "❌ Tiene 2 quants con 123.45 kg reservados - liberar primero en Odoo"
    }
  ],
  "global_error": null  // Solo presente si hay error global
}
```

### En Caso de Error Global

```json
{
  "success_count": 0,
  "error_count": 5,
  "total_kg": 0.0,
  "details": [/* ... todos los pallets con mismo error ... */],
  "global_error": "Ubicación destino es de tipo 'customer' (debe ser 'internal' o 'view')"
}
```

---

## 🎯 Beneficios del Sistema de Validaciones

1. **Prevención**: Detecta problemas antes de ejecutar
2. **Claridad**: Mensajes de error específicos y accionables
3. **Seguridad**: Rollback automático si algo falla
4. **Auditoría**: Log detallado (cuando está disponible)
5. **Resiliencia**: Un error no bloquea el resto de pallets
6. **Información**: Respuesta rica con detalles de cada operación

---

## 🔧 Mantenimiento

### Agregar Nueva Validación

1. Ubicar el punto en el código (`validaciones globales` o `por pallet`)
2. Implementar verificación con mensaje claro
3. Documentar en este archivo
4. Agregar caso de prueba

### Monitoreo

- Los errores de log se imprimen en consola del backend
- Revisar logs si los movimientos no aparecen en "Trasferencias Dashboard"
- Verificar permisos de acceso al modelo de log si falla sistemáticamente
