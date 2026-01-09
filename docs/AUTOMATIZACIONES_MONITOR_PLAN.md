# Plan de Revisión y Blindaje - Monitor de Automatizaciones

**Fecha:** 2026-01-09  
**Objetivo:** Blindar el módulo de Monitor de Órdenes para que detecte y gestione correctamente pallets que cambian de estado (pendiente → disponible)

---

## 1. ANÁLISIS DEL FLUJO ACTUAL

### 1.1 Flujo de Creación de Órdenes
```
Usuario escanea pallets → Validación →
├─ Stock disponible: Se agrega a componentes de MO
└─ Stock NO disponible (recepción abierta): 
   └─ Se registra en JSON `x_studio_pending_receptions`
      {
        "pending": true,
        "pallets": [{codigo, kg, producto_id, picking_id, lot_id}],
        "picking_ids": [...]
      }
```

### 1.2 Flujo de Monitoreo (Estado Actual)
```
Monitor de Órdenes →
├─ Ver detalle de pendientes →
│  └─ API: GET /ordenes/{id}/pendientes
│     └─ Lee JSON x_studio_pending_receptions
│     └─ Verifica cada pallet:
│        ├─ Ya agregado? → ✅ "Ya agregado"
│        ├─ Tiene stock.quant? → 🟢 "Disponible"
│        └─ No tiene stock? → 🟠 "Pendiente"
│
├─ Validar Disponibilidad (mismo endpoint) → Refresca datos
│
├─ Agregar Disponibles →
│  └─ API: POST /ordenes/{id}/agregar-disponibles
│     └─ Agrega pallets con estado "disponible" a componentes de MO
│     └─ NO modifica el JSON
│
└─ Completar Pendientes →
   └─ API: POST /ordenes/{id}/completar-pendientes
      └─ Cambia JSON a {"pending": false}
      └─ Limpia flag de pendientes
```

### 1.3 Problemas Identificados

#### P1: Sin detección de cambios
- Cuando se cierra una recepción, el pallet pasa a stock
- Al hacer "Validar Disponibilidad", sí detecta el cambio (🟠→🟢)
- **PERO** no hay indicación visual de QUÉ cambió desde la última validación

#### P2: Estado "Ya agregado" ambiguo
- Un pallet puede estar en estado "✅ Ya agregado"
- No se sabe SI fue agregado manualmente o auto-agregado por "Agregar Disponibles"
- No hay timestamp de cuándo se agregó

#### P3: "Completar Pendientes" requiere validación manual
- El botón aparece cuando `todos_listos = true`
- Pero el usuario debe verificar manualmente que todos están agregados
- No hay confirmación de seguridad

#### P4: JSON no se actualiza tras agregar
- El JSON `x_studio_pending_receptions` mantiene la lista completa
- Aunque los pallets ya estén en componentes, siguen en el JSON
- Solo se limpia al hacer "Completar Pendientes"

---

## 2. PLAN DE MEJORAS

### 2.1 MEJORA #1: Columna "Estado/Cambios" Mejorada
**Objetivo:** Mostrar cambios de estado visualmente

**Implementación:**
```python
# Backend: obtener_detalle_pendientes()
# Agregar campo "cambio_detectado" a cada pallet

resultado_pallets.append({
    'codigo': codigo,
    'kg': kg,
    'estado': estado,  # 'agregado', 'disponible', 'pendiente'
    'estado_label': estado_label,
    'estado_anterior': estado_anterior,  # Requiere persistencia
    'cambio_detectado': estado != estado_anterior,
    'timestamp_cambio': datetime.now() if cambio else None,
    'picking_name': picking_name,
    ...
})
```

**Frontend:**
```python
# tab_monitor.py - Tabla de pallets
df_pallets = pd.DataFrame([
    {
        'Código': p['codigo'],
        'Kg': f"{p['kg']:,.2f}",
        'Estado': p['estado_label'],
        'Cambios': '🆕 Disponible!' if p.get('cambio_detectado') and p['estado'] == 'disponible' else '',
        'Recepción': p.get('picking_name', 'N/A')
    }
    for p in pallets
])
```

### 2.2 MEJORA #2: Persistencia de Estado Anterior
**Objetivo:** Comparar estado actual vs anterior para detectar cambios

**Opción A - Guardar en JSON (Recomendada):**
```python
# Estructura extendida en x_studio_pending_receptions
{
  "pending": true,
  "pallets": [
    {
      "codigo": "PACK0015749",
      "kg": 412.38,
      "producto_id": 1234,
      "picking_id": 5678,
      "estado_ultima_revision": "pendiente",  # NUEVO
      "timestamp_ultima_revision": "2026-01-08T15:30:00",  # NUEVO
      "fecha_disponible": null  # Se llena cuando pasa a disponible
    }
  ],
  "historial_revisiones": [  # NUEVO - log de validaciones
    {
      "timestamp": "2026-01-09T10:00:00",
      "pendientes": 5,
      "disponibles": 0,
      "agregados": 0
    }
  ]
}
```

**Opción B - Tabla separada:**
```sql
CREATE TABLE automatizaciones_estado_pallets (
    id SERIAL PRIMARY KEY,
    mo_id INT,
    codigo_pallet VARCHAR(50),
    estado VARCHAR(20),
    timestamp TIMESTAMP DEFAULT NOW()
);
```
*Nota: Requiere BD externa, más complejo*

### 2.3 MEJORA #3: Notificaciones Visuales
**Objetivo:** Alertar cuando hay pallets recién disponibles

**Implementación:**
```python
# tab_monitor.py
if detalle.get('hay_cambios_nuevos'):
    nuevos_disponibles = detalle.get('nuevos_disponibles', 0)
    st.success(f"🎉 {nuevos_disponibles} pallet(s) ahora disponible(s)! Click en 'Agregar Disponibles'")

# Backend: obtener_detalle_pendientes()
# Agregar lógica de comparación
nuevos_disponibles = [
    p for p in resultado_pallets 
    if p['estado'] == 'disponible' and p.get('cambio_detectado')
]

return {
    ...
    'hay_cambios_nuevos': len(nuevos_disponibles) > 0,
    'nuevos_disponibles': len(nuevos_disponibles),
    ...
}
```

### 2.4 MEJORA #4: Botón "Agregar Disponibles" Mejorado
**Objetivo:** Actualizar JSON tras agregar

**Backend - agregar_componentes_disponibles():**
```python
def agregar_componentes_disponibles(self, mo_id: int) -> Dict:
    # ... código actual de agregar ...
    
    # NUEVO: Actualizar JSON
    pending_data = json.loads(mo_data['x_studio_pending_receptions'])
    
    # Marcar pallets agregados
    for pallet in pending_data['pallets']:
        if pallet['codigo'] in codigos_agregados:
            pallet['estado_ultima_revision'] = 'agregado'
            pallet['timestamp_agregado'] = datetime.now().isoformat()
    
    # Actualizar historial
    if 'historial_revisiones' not in pending_data:
        pending_data['historial_revisiones'] = []
    
    pending_data['historial_revisiones'].append({
        'timestamp': datetime.now().isoformat(),
        'accion': 'agregar_disponibles',
        'cantidad': len(codigos_agregados),
        'pallets': codigos_agregados
    })
    
    # Guardar JSON actualizado
    self.odoo.write('mrp.production', [mo_id], {
        'x_studio_pending_receptions': json.dumps(pending_data)
    })
```

### 2.5 MEJORA #5: Botón "Completar Pendientes" con Validación
**Objetivo:** Confirmar que TODO está agregado antes de completar

**Frontend:**
```python
with col_b:
    if detalle.get('todos_listos'):
        pendientes_sin_agregar = [
            p for p in pallets 
            if p['estado'] in ['pendiente', 'disponible']
        ]
        
        if pendientes_sin_agregar:
            st.warning(f"⚠️ Aún quedan {len(pendientes_sin_agregar)} sin agregar")
        else:
            if st.button("☑️ Completar Pendientes", 
                        key=f"completar_{orden_id}",
                        help="Marca todos los pendientes como completados"):
                # Confirmación adicional
                confirmar = st.checkbox(
                    f"Confirmo que todos los {len(pallets)} pallets están agregados",
                    key=f"confirm_completar_{orden_id}"
                )
                if confirmar:
                    resp = completar_pendientes(username, password, orden_id)
                    if resp and resp.status_code == 200:
                        st.success("✅ Pendientes completados!")
                        st.cache_data.clear()
                        st.rerun()
```

**Backend - completar_pendientes():**
```python
def completar_pendientes(self, mo_id: int) -> Dict:
    # NUEVO: Validar que todos estén agregados
    detalle = self.obtener_detalle_pendientes(mo_id)
    
    pendientes_restantes = [
        p for p in detalle['pallets'] 
        if p['estado'] != 'agregado'
    ]
    
    if pendientes_restantes:
        return {
            'success': False,
            'error': f"Aún quedan {len(pendientes_restantes)} pallets sin agregar",
            'pendientes_restantes': [p['codigo'] for p in pendientes_restantes]
        }
    
    # Marcar como completado
    self.odoo.write('mrp.production', [mo_id], {
        'x_studio_pending_receptions': json.dumps({'pending': False, 'completed_at': datetime.now().isoformat()})
    })
    
    return {
        'success': True,
        'mensaje': 'Todos los pendientes completados correctamente'
    }
```

### 2.6 MEJORA #6: Indicador de Progreso
**Objetivo:** Mostrar progreso visual de pendientes

**Frontend:**
```python
# tab_monitor.py - en el expander de pendientes
resumen = detalle.get('resumen', {})
total = resumen.get('total', 0)
agregados = resumen.get('agregados', 0)
disponibles = resumen.get('disponibles', 0)
pendientes = resumen.get('pendientes', 0)

progreso = (agregados / total * 100) if total > 0 else 0

st.progress(progreso / 100)
st.markdown(f"""
**Progreso:** {agregados}/{total} agregados ({progreso:.0f}%)  
✅ {agregados} agregados | 🟢 {disponibles} disponibles | 🟠 {pendientes} pendientes
""")
```

---

## 3. CASOS DE PRUEBA

### Caso 1: Creación con Pallets Mixtos
```
DADO: Crear orden con 5 pallets (3 disponibles, 2 en recepción abierta)
CUANDO: Se crea la orden
ENTONCES:
  - 3 pallets deben aparecer en componentes
  - 2 pallets en JSON x_studio_pending_receptions
  - Estado: "stock_pendiente"
```

### Caso 2: Cierre de Recepción
```
DADO: Orden con 2 pallets pendientes
CUANDO: Se aprueba la recepción en Odoo
  Y se hace "Validar Disponibilidad"
ENTONCES:
  - Pallets deben cambiar de 🟠 a 🟢
  - Columna "Cambios" debe mostrar "🆕 Disponible!"
  - Botón "Agregar Disponibles" debe aparecer
```

### Caso 3: Agregar Disponibles
```
DADO: 2 pallets en estado 🟢 Disponible
CUANDO: Click en "Agregar Disponibles"
ENTONCES:
  - Pallets se agregan a componentes de MO
  - Estado cambia a ✅ Ya agregado
  - JSON se actualiza con timestamp
  - Progreso aumenta
```

### Caso 4: Completar Pendientes
```
DADO: Todos los pallets en estado "agregado"
CUANDO: Click en "Completar Pendientes"
ENTONCES:
  - JSON cambia a {"pending": false}
  - Orden sale del filtro "stock_pendiente"
  - Confirmación de éxito
```

### Caso 5: Intentar Completar con Pendientes
```
DADO: 1 pallet aún en estado 🟠 Pendiente
CUANDO: Click en "Completar Pendientes"
ENTONCES:
  - Error: "Aún quedan pallets sin agregar"
  - No se completa la acción
```

---

## 4. PRIORIZACIÓN DE TAREAS

### 🔴 CRÍTICO (Implementar Ya)
1. **Persistencia de estado anterior** (JSON extendido) - Base para todo
2. **Detección de cambios** - Comparar estado actual vs anterior
3. **Validación en Completar Pendientes** - Evitar errores

### 🟡 IMPORTANTE (Siguiente Sprint)
4. **Columna "Cambios"** - UX mejorada
5. **Notificaciones visuales** - Alertas de cambios
6. **Actualizar JSON tras agregar** - Mantener sincronía

### 🟢 MEJORA (Nice to Have)
7. **Indicador de progreso** - Visual feedback
8. **Historial de revisiones** - Auditoría completa
9. **Tests automatizados** - Cobertura de casos

---

## 5. IMPLEMENTACIÓN TÉCNICA DETALLADA

### 5.1 Archivo: `backend/services/tuneles_service.py`

**Método: `obtener_detalle_pendientes()` - Mejorado**

```python
def obtener_detalle_pendientes(self, mo_id: int) -> Dict:
    """
    Obtiene el detalle de los pallets pendientes, detectando cambios de estado.
    """
    import json
    from datetime import datetime
    
    # Leer MO
    mo_data = self.odoo.read('mrp.production', [mo_id], 
        ['name', 'x_studio_pending_receptions', 'move_raw_ids'])[0]
    
    pending_json = mo_data.get('x_studio_pending_receptions')
    if not pending_json:
        return {'success': True, 'tiene_pendientes': False, 'pallets': []}
    
    pending_data = json.loads(pending_json) if isinstance(pending_json, str) else pending_json
    
    if not pending_data.get('pending'):
        return {'success': True, 'tiene_pendientes': False, 'pallets': []}
    
    pallets_info = pending_data.get('pallets', [])
    
    # Obtener componentes existentes
    move_raw_ids = mo_data.get('move_raw_ids', [])
    componentes_existentes = set()
    if move_raw_ids:
        moves = self.odoo.search_read(
            'stock.move.line',
            [('move_id', 'in', move_raw_ids)],
            ['package_id']
        )
        for m in moves:
            if m.get('package_id'):
                componentes_existentes.add(m['package_id'][1])
    
    # Verificar disponibilidad y cambios
    resultado_pallets = []
    cambios_detectados = 0
    
    for p in pallets_info:
        codigo = p.get('codigo', '')
        estado_anterior = p.get('estado_ultima_revision', 'pendiente')
        
        # Verificar si ya fue agregado
        ya_agregado = codigo in componentes_existentes
        
        # Verificar stock
        quants = self.odoo.search_read(
            'stock.quant',
            [
                ('package_id.name', '=', codigo),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal')
            ],
            ['quantity'],
            limit=1
        )
        tiene_stock = len(quants) > 0
        
        # Determinar estado actual
        if ya_agregado:
            estado_actual = 'agregado'
            estado_label = '✅ Ya agregado'
        elif tiene_stock:
            estado_actual = 'disponible'
            estado_label = '🟢 Disponible'
        else:
            estado_actual = 'pendiente'
            estado_label = '🟠 Pendiente'
        
        # Detectar cambio
        cambio = (estado_actual != estado_anterior)
        if cambio and estado_actual == 'disponible':
            cambios_detectados += 1
        
        resultado_pallets.append({
            'codigo': codigo,
            'kg': p.get('kg', 0),
            'estado': estado_actual,
            'estado_anterior': estado_anterior,
            'estado_label': estado_label,
            'cambio_detectado': cambio,
            'nuevo_disponible': cambio and estado_actual == 'disponible',
            'picking_id': p.get('picking_id'),
            'picking_name': p.get('picking_name', 'N/A'),
        })
    
    # Resumen
    agregados = sum(1 for p in resultado_pallets if p['estado'] == 'agregado')
    disponibles = sum(1 for p in resultado_pallets if p['estado'] == 'disponible')
    pendientes = sum(1 for p in resultado_pallets if p['estado'] == 'pendiente')
    
    return {
        'success': True,
        'mo_id': mo_id,
        'mo_name': mo_data['name'],
        'tiene_pendientes': True,
        'pallets': resultado_pallets,
        'resumen': {
            'total': len(resultado_pallets),
            'agregados': agregados,
            'disponibles': disponibles,
            'pendientes': pendientes
        },
        'hay_cambios_nuevos': cambios_detectados > 0,
        'nuevos_disponibles': cambios_detectados,
        'hay_disponibles_sin_agregar': disponibles > 0,
        'todos_listos': pendientes == 0 and disponibles == 0,
    }
```

**Método: `agregar_componentes_disponibles()` - Con actualización de JSON**

```python
def agregar_componentes_disponibles(self, mo_id: int) -> Dict:
    """
    Agrega pallets disponibles y actualiza JSON de pendientes.
    """
    import json
    from datetime import datetime
    
    # Obtener detalle actual
    detalle = self.obtener_detalle_pendientes(mo_id)
    if not detalle.get('success'):
        return detalle
    
    pallets_disponibles = [
        p for p in detalle['pallets'] 
        if p['estado'] == 'disponible'
    ]
    
    if not pallets_disponibles:
        return {
            'success': False,
            'error': 'No hay pallets disponibles para agregar'
        }
    
    # Agregar cada pallet como componente
    agregados = []
    for pallet_info in pallets_disponibles:
        codigo = pallet_info['codigo']
        
        # Buscar quant
        quants = self.odoo.search_read(
            'stock.quant',
            [
                ('package_id.name', '=', codigo),
                ('quantity', '>', 0),
                ('location_id.usage', '=', 'internal')
            ],
            ['id', 'product_id', 'lot_id', 'quantity', 'location_id', 'package_id'],
            limit=1
        )
        
        if quants:
            quant = quants[0]
            # Agregar move.line (componente)
            # ... código de agregar move line ...
            agregados.append(codigo)
    
    # NUEVO: Actualizar JSON
    mo_data = self.odoo.read('mrp.production', [mo_id], ['x_studio_pending_receptions'])[0]
    pending_json = mo_data.get('x_studio_pending_receptions')
    pending_data = json.loads(pending_json)
    
    # Actualizar estado de pallets agregados
    for pallet in pending_data['pallets']:
        if pallet['codigo'] in agregados:
            pallet['estado_ultima_revision'] = 'agregado'
            pallet['timestamp_agregado'] = datetime.now().isoformat()
    
    # Agregar al historial
    if 'historial_revisiones' not in pending_data:
        pending_data['historial_revisiones'] = []
    
    pending_data['historial_revisiones'].append({
        'timestamp': datetime.now().isoformat(),
        'accion': 'agregar_disponibles',
        'cantidad': len(agregados),
        'pallets': agregados
    })
    
    # Guardar
    self.odoo.write('mrp.production', [mo_id], {
        'x_studio_pending_receptions': json.dumps(pending_data)
    })
    
    return {
        'success': True,
        'agregados': len(agregados),
        'mensaje': f'Se agregaron {len(agregados)} pallet(s) disponible(s)',
        'pallets_agregados': agregados
    }
```

**Método: `completar_pendientes()` - Con validación estricta**

```python
def completar_pendientes(self, mo_id: int) -> Dict:
    """
    Completa pendientes solo si TODOS están agregados.
    """
    import json
    from datetime import datetime
    
    # Verificar estado actual
    detalle = self.obtener_detalle_pendientes(mo_id)
    if not detalle.get('success'):
        return detalle
    
    # Validar que NO queden pendientes ni disponibles
    pendientes_restantes = [
        p for p in detalle['pallets'] 
        if p['estado'] in ['pendiente', 'disponible']
    ]
    
    if pendientes_restantes:
        return {
            'success': False,
            'error': f"Aún quedan {len(pendientes_restantes)} pallets sin agregar",
            'pendientes_restantes': [p['codigo'] for p in pendientes_restantes]
        }
    
    # Marcar como completado
    mo_data = self.odoo.read('mrp.production', [mo_id], ['x_studio_pending_receptions'])[0]
    pending_json = mo_data.get('x_studio_pending_receptions')
    pending_data = json.loads(pending_json)
    
    pending_data['pending'] = False
    pending_data['completed_at'] = datetime.now().isoformat()
    pending_data['completed_by'] = 'automatic'
    
    self.odoo.write('mrp.production', [mo_id], {
        'x_studio_pending_receptions': json.dumps(pending_data)
    })
    
    return {
        'success': True,
        'mensaje': f'Completados {len(detalle["pallets"])} pendientes correctamente'
    }
```

---

## 6. CRONOGRAMA DE IMPLEMENTACIÓN

| Día | Tareas | Tiempo Est. |
|-----|--------|-------------|
| **D1** | Extender JSON schema + Actualizar obtener_detalle_pendientes | 2-3h |
| **D2** | Modificar agregar_componentes_disponibles + Tests | 2h |
| **D3** | Mejorar completar_pendientes con validación | 1h |
| **D4** | Frontend: Columna cambios + Notificaciones | 2h |
| **D5** | Testing completo con orden real + Ajustes | 2h |
| **TOTAL** | | **9-10 horas** |

---

## 7. CHECKLIST DE VERIFICACIÓN FINAL

- [ ] JSON tiene campo `estado_ultima_revision` en cada pallet
- [ ] JSON tiene campo `historial_revisiones` general
- [ ] Backend detecta cambios comparando estado actual vs anterior
- [ ] Frontend muestra columna "Cambios" con 🆕 para disponibles
- [ ] Botón "Agregar Disponibles" actualiza JSON tras agregar
- [ ] Botón "Completar Pendientes" valida que todos estén agregados
- [ ] Notificación visual cuando hay pallets recién disponibles
- [ ] Indicador de progreso muestra avance correcto
- [ ] Caso de prueba 1: Creación mixta ✅
- [ ] Caso de prueba 2: Detección de cambio ✅
- [ ] Caso de prueba 3: Agregar disponibles ✅
- [ ] Caso de prueba 4: Completar exitoso ✅
- [ ] Caso de prueba 5: Completar bloqueado ✅
- [ ] Deploy a DEV
- [ ] Testing con orden real del usuario
- [ ] Deploy a PROD

---

**FIN DEL PLAN**
