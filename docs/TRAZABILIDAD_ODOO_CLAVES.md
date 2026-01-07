# 🔗 TRAZABILIDAD EN ODOO: CLAVES DE RELACIÓN Y EJEMPLO TÉCNICO

## 📊 DIAGRAMA DE FLUJO

Ver imagen: `trazabilidad_odoo_diagram.png`

---

## 🔑 CLAVES DE RELACIÓN (FOREIGN KEYS)

### **TABLA DE RELACIONES**

| Modelo Origen | Campo (FK) | Modelo Destino | Descripción |
|---------------|------------|----------------|-------------|
| `sale.order.line` | `order_id` | `sale.order` | Línea → Orden de venta |
| `stock.picking` | `origin` | `sale.order.name` | Picking → Orden de venta (por nombre) |
| `stock.move.line` | `picking_id` | `stock.picking` | Movimiento detallado → Picking |
| `stock.move.line` | `lot_id` | `stock.lot` | Movimiento → Lote/Serie |
| `stock.move.line` | `result_package_id` | `stock.quant.package` | Movimiento → Paquete/Pallet resultante |
| `stock.move.line` | `move_id` | `stock.move` | Movimiento detallado → Movimiento general |
| `stock.move` | `production_id` | `mrp.production` | Movimiento → Orden de manufactura (producto terminado) |
| `stock.move` | `raw_material_production_id` | `mrp.production` | Movimiento → Orden de manufactura (consumo) |
| `mrp.production` | `move_raw_ids` | `stock.move` | MO → Movimientos de consumo (1:N) |
| `mrp.production` | `move_finished_ids` | `stock.move` | MO → Movimientos de producción (1:N) |
| `mrp.production` | `lot_producing_id` | `stock.lot` | MO → Lote que está produciendo |
| `stock.picking` | `partner_id` | `res.partner` | Picking → Proveedor/Cliente |
| `stock.picking` | `location_id` | `stock.location` | Picking → Ubicación origen |
| `stock.picking` | `location_dest_id` | `stock.location` | Picking → Ubicación destino |

---

## 📦 EJEMPLO COMPLETO: PALLET "PALLET-RF-2024-0156"

### **CONTEXTO INICIAL**
- **Cliente:** Camerican Berries LLC
- **Producto:** Frambuesa IQF A - Retail 1kg
- **Pallet Enviado:** PALLET-RF-2024-0156 (500 kg)
- **Pregunta:** ¿De qué productor vino esta fruta?

---

## 🔍 PASO A PASO CON QUERIES REALES

### **1️⃣ VENTA → Identificar el Pallet**

#### **Query 1.1: Buscar la orden de venta**
```python
# Dato inicial: Cliente "Camerican Berries LLC"
sale_order = {
    'id': 5678,
    'name': 'S00892',
    'partner_id': [1234, 'Camerican Berries LLC'],
    'date_order': '2024-12-20'
}
```

#### **Query 1.2: Buscar el picking de entrega**
```python
odoo.search_read(
    'stock.picking',
    [
        ['origin', '=', 'S00892'],  # ← CLAVE: origin vincula con sale.order.name
        ['picking_type_id.code', '=', 'outgoing']
    ],
    ['id', 'name', 'state']
)

# RESULTADO:
{
    'id': 9876,
    'name': 'WH/OUT/2024/0523',
    'state': 'done'
}
```
**🔑 CLAVE:** `stock.picking.origin` = `sale.order.name` (relación por texto)

#### **Query 1.3: Encontrar el pallet específico**
```python
odoo.search_read(
    'stock.move.line',
    [['picking_id', '=', 9876]],  # ← CLAVE: picking_id → stock.picking.id
    ['id', 'lot_id', 'result_package_id', 'qty_done']
)

# RESULTADO:
{
    'id': 45623,
    'lot_id': [7891, 'LOTE-PT-2024-0892'],              # ← LOTE
    'result_package_id': [3344, 'PALLET-RF-2024-0156'],  # ← PALLET
    'qty_done': 500
}
```
**🔑 CLAVES:**
- `stock.move.line.picking_id` → `stock.picking.id` (ID numérico)
- `stock.move.line.lot_id` → `stock.lot.id` (ID numérico)
- `stock.move.line.result_package_id` → `stock.quant.package.id` (ID numérico)

---

### **2️⃣ PRODUCCIÓN → Rastrear el Lote al Packing**

#### **Query 2.1: Buscar todos los movimientos del lote PT**
```python
odoo.search_read(
    'stock.move.line',
    [['lot_id', '=', 7891]],  # ← CLAVE: lot_id → stock.lot.id
    ['id', 'move_id', 'date', 'location_id', 'location_dest_id'],
    order='date asc'
)

# RESULTADO (primer movimiento = creación):
{
    'id': 44001,
    'move_id': [88912, 'Stock Move'],  # ← MOVE_ID
    'date': '2024-12-15 14:30:00',
    'location_id': [22, 'WH/Production'],      # Origen: Producción
    'location_dest_id': [14, 'WH/Stock/Congelado']  # Destino: Stock
}
```
**🔑 CLAVE:** `stock.move.line.move_id` → `stock.move.id`

#### **Query 2.2: Del move obtener la MO**
```python
odoo.search_read(
    'stock.move',
    [['id', '=', 88912]],  # ← Del move_id anterior
    ['id', 'production_id', 'raw_material_production_id']
)

# RESULTADO:
{
    'id': 88912,
    'production_id': [4523, 'MO/PACK/2024/0892']  # ← ORDEN DE MANUFACTURA
}
```
**🔑 CLAVE:** `stock.move.production_id` → `mrp.production.id`
- **Nota:** Si el move es de consumo, usar `raw_material_production_id` en su lugar

#### **Query 2.3: Obtener consumos de la MO**
```python
# Primero obtener la MO completa
odoo.search_read(
    'mrp.production',
    [['id', '=', 4523]],
    ['id', 'name', 'move_raw_ids', 'move_finished_ids']
)

# RESULTADO:
{
    'id': 4523,
    'name': 'MO/PACK/2024/0892',
    'move_raw_ids': [88900, 88901],  # ← IDs de movimientos de consumo
    'move_finished_ids': [88912]
}

# Luego buscar los consumos detallados
odoo.search_read(
    'stock.move.line',
    [['move_id', 'in', [88900, 88901]]],  # ← CLAVE: move_id in move_raw_ids
    ['id', 'product_id', 'lot_id', 'qty_done']
)

# RESULTADO:
[
    {
        'id': 43998,
        'product_id': [445, '[1.12001] Frambuesa IQF Proceso Congelado'],
        'lot_id': [6712, 'LOTE-CONG-2024-0445'],  # ← LOTE INTERMEDIO
        'qty_done': 520
    },
    {
        'id': 43999,
        'product_id': [889, 'Caja Retail 1kg'],  # Insumo (sin lote)
        'lot_id': False,
        'qty_done': 500
    }
]
```
**🔑 CLAVES:**
- `mrp.production.move_raw_ids` → `stock.move.id` (relación 1:N)
- `mrp.production.move_finished_ids` → `stock.move.id` (relación 1:N)
- `stock.move.id` → `stock.move.line.move_id` (1:N)

---

### **3️⃣ PROCESO → Del Congelado al Vaciado**

#### **Query 3.1: Rastrear el lote de congelado**
```python
# Buscar primer movimiento del lote LOTE-CONG-2024-0445
odoo.search_read(
    'stock.move.line',
    [['lot_id', '=', 6712]],
    ['id', 'move_id', 'date'],
    order='date asc',
    limit=1
)

# RESULTADO:
{
    'id': 42001,
    'move_id': [87500, 'Stock Move'],
    'date': '2024-12-14 18:00:00'
}
```

#### **Query 3.2: Obtener MO de congelado**
```python
odoo.search_read(
    'stock.move',
    [['id', '=', 87500]],
    ['production_id']
)

# RESULTADO:
{
    'production_id': [4480, 'MO/TUNEL/2024/0156']
}

# Obtener consumos de la MO de congelado
odoo.search_read(
    'mrp.production',
    [['id', '=', 4480]],
    ['move_raw_ids']
)

# RESULTADO:
{
    'move_raw_ids': [87450]
}

# Buscar el lote consumido
odoo.search_read(
    'stock.move.line',
    [['move_id', '=', 87450]],
    ['lot_id', 'product_id', 'qty_done']
)

# RESULTADO:
{
    'lot_id': [5890, 'LOTE-VAC-2024-0223'],  # ← LOTE DE VACIADO
    'product_id': [334, '[3] Frambuesa Proceso Vaciado'],
    'qty_done': 800
}
```

---

### **4️⃣ PROCESO → Del Vaciado a la Materia Prima**

#### **Query 4.1: Rastrear el lote de vaciado**
```python
# Primer movimiento del lote LOTE-VAC-2024-0223
odoo.search_read(
    'stock.move.line',
    [['lot_id', '=', 5890]],
    ['move_id', 'date'],
    order='date asc',
    limit=1
)

# RESULTADO:
{
    'move_id': [86200, 'Stock Move'],
    'date': '2024-12-14 12:00:00'
}
```

#### **Query 4.2: Obtener MO de vaciado**
```python
odoo.search_read(
    'stock.move',
    [['id', '=', 86200]],
    ['production_id']
)

# RESULTADO:
{
    'production_id': [4401, 'MO/SALA3/2024/0223']
}

# Consumos de la MO de vaciado
odoo.search_read(
    'mrp.production',
    [['id', '=', 4401]],
    ['move_raw_ids', 'x_studio_sala_de_proceso']
)

# RESULTADO:
{
    'move_raw_ids': [86150],
    'x_studio_sala_de_proceso': 'Sala 3'
}

# Lote de MP consumido
odoo.search_read(
    'stock.move.line',
    [['move_id', '=', 86150]],
    ['lot_id', 'product_id', 'qty_done']
)

# RESULTADO:
{
    'lot_id': [4512, 'MP-2024-1892'],  # ← LOTE DE MATERIA PRIMA
    'product_id': [223, '[3000012] Frambuesa Fresca Orgánica'],
    'qty_done': 1000
}
```

---

### **5️⃣ RECEPCIÓN → Del Lote MP al Productor**

#### **Query 5.1: Buscar el picking de recepción**
```python
# Buscar movimientos del lote MP donde location_id sea "Vendors"
odoo.search_read(
    'stock.move.line',
    [
        ['lot_id', '=', 4512],  # ← LOTE MP
        ['location_id.usage', '=', 'supplier']  # Origen = proveedor
    ],
    ['id', 'picking_id', 'date', 'location_id'],
    order='date asc',
    limit=1
)

# RESULTADO:
{
    'id': 38001,
    'picking_id': [8234, 'WH/IN/2024/0445'],
    'date': '2024-12-10 08:30:00',
    'location_id': [8, 'Partners/Vendors']
}
```
**🔑 CLAVE:** `stock.move.line.picking_id` → `stock.picking.id`

#### **Query 5.2: Obtener el productor**
```python
odoo.search_read(
    'stock.picking',
    [['id', '=', 8234]],
    ['id', 'name', 'partner_id', 'scheduled_date', 'origin']
)

# RESULTADO:
{
    'id': 8234,
    'name': 'WH/IN/2024/0445',
    'partner_id': [789, 'Agrícola San José S.A.'],  # ← PRODUCTOR
    'scheduled_date': '2024-12-10 08:30:00',
    'origin': 'Compra/2024/0089'
}
```
**🔑 CLAVE:** `stock.picking.partner_id` → `res.partner.id`

#### **Query 5.3: Información completa del productor**
```python
odoo.search_read(
    'res.partner',
    [['id', '=', 789]],
    ['id', 'name', 'vat', 'phone', 'email', 'street', 'city']
)

# RESULTADO:
{
    'id': 789,
    'name': 'Agrícola San José S.A.',
    'vat': '76.123.456-7',
    'phone': '+56 9 8765 4321',
    'email': 'contacto@agricolasanjose.cl',
    'street': 'Camino Agrícola Km 12',
    'city': 'Los Ángeles'
}
```

---

## 🎯 RESULTADO FINAL DE LA TRAZABILIDAD

```python
{
    "pallet": "PALLET-RF-2024-0156",
    "cliente": "Camerican Berries LLC",
    "fecha_venta": "2024-12-22",
    "kg_vendidos": 500,
    
    "cadena_produccion": [
        {
            "etapa": "PACKING",
            "mo": "MO/PACK/2024/0892",
            "fecha": "2024-12-15 14:30:00",
            "sala": "Línea Retail",
            "lote_producido": "LOTE-PT-2024-0892",
            "kg_producidos": 500,
            "kg_consumidos": 520,
            "rendimiento": 96.15
        },
        {
            "etapa": "CONGELADO",
            "mo": "MO/TUNEL/2024/0156",
            "fecha": "2024-12-14 18:00:00",
            "sala": "Túnel Estático",
            "lote_producido": "LOTE-CONG-2024-0445",
            "kg_producidos": 800,
            "kg_consumidos": 800,
            "rendimiento": 100
        },
        {
            "etapa": "VACIADO",
            "mo": "MO/SALA3/2024/0223",
            "fecha": "2024-12-14 12:00:00",
            "sala": "Sala 3",
            "lote_producido": "LOTE-VAC-2024-0223",
            "kg_producidos": 800,
            "kg_consumidos": 1000,
            "rendimiento": 80
        }
    ],
    
    "materia_prima": {
        "lote": "MP-2024-1892",
        "producto": "[3000012] Frambuesa Fresca Orgánica",
        "kg": 1000,
        "fecha_recepcion": "2024-12-10 08:30:00"
    },
    
    "productor": {
        "id": 789,
        "nombre": "Agrícola San José S.A.",
        "rut": "76.123.456-7",
        "contacto": "+56 9 8765 4321",
        "direccion": "Camino Agrícola Km 12, Los Ángeles"
    },
    
    "trazabilidad_completa": "VENTA → PACKING (96%) → CONGELADO (100%) → VACIADO (80%) → MP (1000kg) → PRODUCTOR",
    "rendimiento_total": 50,  # 500kg PT / 1000kg MP = 50%
    "merma_total": 500  # 1000kg MP - 500kg PT = 500kg
}
```

---

## 🔧 FUNCIONES CLAVE PARA IMPLEMENTAR

### **Función 1: Obtener MO desde un Lote**
```python
def get_mo_from_lot(odoo, lot_id, es_consumo=False):
    """
    Obtiene la MO que produjo o consumió un lote.
    
    Args:
        lot_id: ID del lote (stock.lot)
        es_consumo: False = lote producido, True = lote consumido
    
    Returns:
        mrp.production record
    """
    # Buscar primer movimiento del lote
    moves = odoo.search_read(
        'stock.move.line',
        [['lot_id', '=', lot_id]],
        ['move_id', 'date'],
        order='date asc',
        limit=1
    )
    
    if not moves:
        return None
    
    move_id = moves[0]['move_id'][0]
    
    # Obtener la MO
    move = odoo.search_read(
        'stock.move',
        [['id', '=', move_id]],
        ['production_id', 'raw_material_production_id']
    )
    
    if not move:
        return None
    
    # Según si es consumo o producción
    if es_consumo:
        mo_id = move[0].get('raw_material_production_id')
    else:
        mo_id = move[0].get('production_id')
    
    if not mo_id:
        return None
    
    return odoo.search_read(
        'mrp.production',
        [['id', '=', mo_id[0]]],
        ['id', 'name', 'move_raw_ids', 'date_planned_start', 'x_studio_sala_de_proceso']
    )[0]
```

### **Función 2: Obtener Consumos de una MO**
```python
def get_consumos_mo(odoo, mo_id):
    """
    Obtiene todos los lotes consumidos por una MO.
    
    Args:
        mo_id: ID de la MO (mrp.production)
    
    Returns:
        Lista de consumos con lote, producto y cantidad
    """
    # Obtener move_raw_ids de la MO
    mo = odoo.search_read(
        'mrp.production',
        [['id', '=', mo_id]],
        ['move_raw_ids']
    )[0]
    
    if not mo.get('move_raw_ids'):
        return []
    
    # Obtener stock.move.line de los consumos
    consumos = odoo.search_read(
        'stock.move.line',
        [['move_id', 'in', mo['move_raw_ids']]],
        ['product_id', 'lot_id', 'qty_done']
    )
    
    # Filtrar solo los que tienen lote (excluir insumos)
    return [c for c in consumos if c.get('lot_id')]
```

### **Función 3: Obtener Productor de un Lote MP**
```python
def get_productor_from_lot(odoo, lot_id):
    """
    Obtiene el productor original de un lote MP.
    
    Args:
        lot_id: ID del lote MP (stock.lot)
    
    Returns:
        res.partner record (productor)
    """
    # Buscar movimientos del lote desde ubicación de proveedor
    moves = odoo.search_read(
        'stock.move.line',
        [
            ['lot_id', '=', lot_id],
            ['location_id.usage', '=', 'supplier']
        ],
        ['picking_id', 'date'],
        order='date asc',
        limit=1
    )
    
    if not moves or not moves[0].get('picking_id'):
        return None
    
    picking_id = moves[0]['picking_id'][0]
    
    # Obtener el picking de recepción
    picking = odoo.search_read(
        'stock.picking',
        [['id', '=', picking_id]],
        ['partner_id', 'scheduled_date']
    )[0]
    
    if not picking.get('partner_id'):
        return None
    
    partner_id = picking['partner_id'][0]
    
    # Obtener información del productor
    return odoo.search_read(
        'res.partner',
        [['id', '=', partner_id]],
        ['id', 'name', 'vat', 'phone', 'email', 'street', 'city']
    )[0]
```

---

## 📚 RESUMEN DE CLAVES PRINCIPALES

### **Navegación Hacia Atrás (PT → MP)**

1. **Venta → Pallet:**
   - `stock.picking.origin` = `sale.order.name`
   - `stock.move.line.picking_id` → `stock.picking.id`
   - `stock.move.line.result_package_id` → Pallet físico

2. **Pallet → Lote PT:**
   - `stock.move.line.lot_id` → `stock.lot.id`

3. **Lote PT → MO:**
   - `stock.move.line.move_id` → `stock.move.id`
   - `stock.move.production_id` → `mrp.production.id`

4. **MO → Lotes Consumidos:**
   - `mrp.production.move_raw_ids` → `stock.move.id` (1:N)
   - `stock.move.id` → `stock.move.line.move_id`
   - `stock.move.line.lot_id` → Lotes MP/intermedios

5. **Lote MP → Productor:**
   - `stock.move.line.lot_id` + `location_id.usage='supplier'`
   - `stock.move.line.picking_id` → `stock.picking.id`
   - `stock.picking.partner_id` → `res.partner.id` (Productor)

### **Campos Críticos por Modelo**

| Modelo | Campos Esenciales |
|--------|-------------------|
| `stock.lot` | `id`, `name`, `product_id`, `create_date` |
| `stock.move.line` | `lot_id`, `move_id`, `picking_id`, `qty_done`, `location_id`, `result_package_id` |
| `stock.move` | `production_id`, `raw_material_production_id` |
| `mrp.production` | `id`, `name`, `move_raw_ids`, `move_finished_ids`, `lot_producing_id` |
| `stock.picking` | `partner_id`, `origin`, `picking_type_id`, `location_id` |
| `res.partner` | `id`, `name`, `vat`, contacto |

---

## ✅ CHECKLIST DE IMPLEMENTACIÓN

- [ ] Estandarizar nomenclatura de lotes (MP-*, PROC-*, CONG-*, PALLET-*)
- [ ] Validar que todas las recepciones tengan `partner_id` válido
- [ ] Registrar todas las etapas como MOs separadas
- [ ] Usar `result_package_id` para rastrear pallets físicos
- [ ] Filtrar insumos en consumos (solo lotes con materia prima)
- [ ] Implementar caché para consultas frecuentes
- [ ] Crear índices en: `lot_id`, `move_id`, `production_id`, `picking_id`
- [ ] Validar `location_id.usage` para identificar recepciones de proveedores

---

**Creado:** 2026-01-07
**Autor:** Sistema de Trazabilidad Rio Futuro
