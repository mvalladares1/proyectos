# 🔑 RESUMEN EJECUTIVO: CLAVES DE TRAZABILIDAD ODOO

## 📊 FLUJO COMPLETO

```
VENTA (sale.order) 
  ↓ [origin]
ENTREGA (stock.picking OUT)
  ↓ [picking_id]
MOVIMIENTO DE SALIDA (stock.move.line)
  ↓ [lot_id]
LOTE PT (stock.lot)
  ↓ [buscar primer move_id]
MOVIMIENTO DE PRODUCCIÓN (stock.move.line)
  ↓ [move_id → production_id]
ORDEN DE MANUFACTURA PACKING (mrp.production)
  ↓ [move_raw_ids]
CONSUMO DE LOTE INTERMEDIO (stock.move.line)
  ↓ [lot_id]
LOTE CONGELADO (stock.lot)
  ↓ [repetir: move_id → production_id]
ORDEN DE MANUFACTURA CONGELADO (mrp.production)
  ↓ [move_raw_ids]
CONSUMO DE LOTE PROCESO (stock.move.line)
  ↓ [lot_id]
LOTE VACIADO (stock.lot)
  ↓ [repetir: move_id → production_id]
ORDEN DE MANUFACTURA VACIADO (mrp.production)
  ↓ [move_raw_ids]
CONSUMO DE MATERIA PRIMA (stock.move.line)
  ↓ [lot_id]
LOTE MP (stock.lot)
  ↓ [buscar move con location_id.usage='supplier']
PICKING DE RECEPCIÓN (stock.picking IN)
  ↓ [partner_id]
PRODUCTOR (res.partner) ✅
```

---

## 🔗 TABLA DE CLAVES CRÍTICAS

| # | Desde | Campo Clave | Hacia | Tipo | Ejemplo |
|---|-------|-------------|-------|------|---------|
| 1 | `sale.order.name` | `origin` | `stock.picking` | String | "S00892" → picking.origin |
| 2 | `stock.picking.id` | `picking_id` | `stock.move.line` | Integer | 9876 → move_line.picking_id |
| 3 | `stock.lot.id` | `lot_id` | `stock.move.line` | Integer | 7891 → move_line.lot_id |
| 4 | `stock.move.id` | `move_id` | `stock.move.line` | Integer | 88912 → move_line.move_id |
| 5 | `mrp.production.id` | `production_id` | `stock.move` | Integer | 4523 → move.production_id |
| 6 | `mrp.production.move_raw_ids` | `move_id` | `stock.move` | Integer[] | [88900, 88901] |
| 7 | `res.partner.id` | `partner_id` | `stock.picking` | Integer | 789 → picking.partner_id |
| 8 | `stock.quant.package.id` | `result_package_id` | `stock.move.line` | Integer | 3344 (PALLET) |

---

## 🎯 LOS 3 QUERIES FUNDAMENTALES

### **Query 1: Del Lote al MO (Producción)**
```python
# Input: lot_id (del lote que quieres rastrear)
# Output: mrp.production (MO que lo produjo)

# Paso 1: Buscar primer movimiento del lote
move_line = odoo.search_read(
    'stock.move.line',
    [['lot_id', '=', LOT_ID]],
    ['move_id'],
    order='date asc',
    limit=1
)[0]

# Paso 2: Del move obtener la MO
move = odoo.search_read(
    'stock.move',
    [['id', '=', move_line['move_id'][0]]],
    ['production_id']
)[0]

mo_id = move['production_id'][0]
```

### **Query 2: Del MO a los Lotes Consumidos**
```python
# Input: mo_id (de la MO que quieres analizar)
# Output: Lista de lotes que consumió

# Paso 1: Obtener move_raw_ids de la MO
mo = odoo.search_read(
    'mrp.production',
    [['id', '=', MO_ID]],
    ['move_raw_ids']
)[0]

# Paso 2: Obtener los lotes consumidos
consumos = odoo.search_read(
    'stock.move.line',
    [
        ['move_id', 'in', mo['move_raw_ids']],
        ['lot_id', '!=', False]  # Solo los que tienen lote
    ],
    ['lot_id', 'product_id', 'qty_done']
)

# Resultado: lista de lotes MP/intermedios
```

### **Query 3: Del Lote MP al Productor**
```python
# Input: lot_id (lote de materia prima)
# Output: res.partner (productor)

# Paso 1: Buscar recepción (location de proveedor)
move_line = odoo.search_read(
    'stock.move.line',
    [
        ['lot_id', '=', LOT_ID],
        ['location_id.usage', '=', 'supplier']
    ],
    ['picking_id'],
    order='date asc',
    limit=1
)[0]

# Paso 2: Del picking obtener el partner
picking = odoo.search_read(
    'stock.picking',
    [['id', '=', move_line['picking_id'][0]]],
    ['partner_id']
)[0]

productor_id = picking['partner_id'][0]
```

---

## 📦 EJEMPLO CON DATOS REALES

### **Entrada: PALLET-RF-2024-0156**

| Paso | Modelo | Query Campo | Valor | Resultado |
|------|--------|-------------|-------|-----------|
| 1 | `stock.move.line` | `result_package_id.name = "PALLET-RF-2024-0156"` | → | `lot_id = 7891` |
| 2 | `stock.lot` | `id = 7891` | → | `LOTE-PT-2024-0892` |
| 3 | `stock.move.line` | `lot_id = 7891` (orden asc) | → | `move_id = 88912` |
| 4 | `stock.move` | `id = 88912` | → | `production_id = 4523` |
| 5 | `mrp.production` | `id = 4523` | → | **MO/PACK/2024/0892** |
| 6 | `mrp.production` | `move_raw_ids` | → | `[88900]` |
| 7 | `stock.move.line` | `move_id = 88900` | → | `lot_id = 6712` |
| 8 | `stock.lot` | `id = 6712` | → | `LOTE-CONG-2024-0445` |
| 9 | Repetir 3-8 | ... | → | `LOTE-VAC-2024-0223` |
| 10 | Repetir 3-8 | ... | → | `LOTE MP-2024-1892` ✅ |
| 11 | `stock.move.line` | `lot_id = 4512` + `location.usage = supplier` | → | `picking_id = 8234` |
| 12 | `stock.picking` | `id = 8234` | → | `partner_id = 789` |
| 13 | `res.partner` | `id = 789` | → | **Agrícola San José S.A.** ✅ |

---

## 🔍 CAMPOS DISCRIMINADORES

### **Para Identificar Tipo de Movimiento:**

| Campo | Valor | Significado |
|-------|-------|-------------|
| `location_id.usage` | `'supplier'` | Entrada de proveedor (RECEPCIÓN) |
| `location_id.usage` | `'customer'` | Salida a cliente (VENTA) |
| `location_id` | `'WH/Production'` | Movimiento de manufactura |
| `picking_type_id.code` | `'incoming'` | Recepción |
| `picking_type_id.code` | `'outgoing'` | Entrega |
| `picking_type_id.code` | `'internal'` | Movimiento interno |
| `stock.move.production_id` | `!= False` | Producto de una MO |
| `stock.move.raw_material_production_id` | `!= False` | Consumo de una MO |

### **Para Filtrar Insumos vs MP:**

```python
# INCLUIR (Materia Prima):
- Tiene lot_id
- product_id empieza con [3] o [1]
- product.template.x_studio_sub_categora != 'Otro'
- product.template.x_studio_categora_tipo_de_manejo != 'Otro'

# EXCLUIR (Insumos):
- lot_id = False
- product_name contiene: 'caja', 'bolsa', 'etiqueta', 'pallet', 'electricidad'
- category_name contiene: 'insumo', 'envase', 'embalaje'
```

---

## ⚡ ALGORITMO RECURSIVO DE TRAZABILIDAD

```python
def trazabilidad_completa(odoo, lot_id_inicial):
    """
    Algoritmo recursivo para rastrear desde PT hasta MP.
    """
    cadena = []
    lotes_procesados = set()
    
    def rastrear_lote(lot_id, nivel=0):
        # Evitar loops infinitos
        if lot_id in lotes_procesados:
            return
        lotes_procesados.add(lot_id)
        
        # 1. Obtener MO que produjo este lote
        mo = get_mo_from_lot(odoo, lot_id)
        
        if not mo:
            # Es MP (no fue producido, fue comprado)
            productor = get_productor_from_lot(odoo, lot_id)
            cadena.append({
                'nivel': nivel,
                'tipo': 'MATERIA_PRIMA',
                'lot_id': lot_id,
                'productor': productor
            })
            return
        
        # 2. Registrar la MO
        cadena.append({
            'nivel': nivel,
            'tipo': 'PROCESO',
            'mo': mo['name'],
            'sala': mo.get('x_studio_sala_de_proceso'),
            'lot_producido': lot_id
        })
        
        # 3. Obtener consumos de la MO
        consumos = get_consumos_mo(odoo, mo['id'])
        
        # 4. Rastrear cada lote consumido (recursión)
        for consumo in consumos:
            lot_consumido = consumo['lot_id'][0]
            rastrear_lote(lot_consumido, nivel + 1)
    
    # Iniciar recursión
    rastrear_lote(lot_id_inicial, 0)
    
    return cadena
```

---

## ✅ VALIDACIONES IMPORTANTES

### **Antes de Rastrear:**
1. ✅ Validar que `lot_id` exista en `stock.lot`
2. ✅ Verificar que el lote tenga movimientos (`stock.move.line`)
3. ✅ Confirmar que `result_package_id` corresponda al pallet buscado

### **Durante el Rastreo:**
1. ✅ Ordenar siempre por `date asc` para encontrar origen
2. ✅ Filtrar `lot_id != False` para excluir insumos sin lote
3. ✅ Usar `limit=1` cuando solo necesitas el primer/último registro
4. ✅ Validar que `production_id` no sea False antes de continuar

### **Identificar Fin de Cadena:**
1. ✅ Si `stock.move.production_id = False` → Es MP (no fue producido)
2. ✅ Si `location_id.usage = 'supplier'` → Es recepción de proveedor
3. ✅ Si no hay más `move_raw_ids` → Llegaste al origen

---

## 🎓 CONCEPTOS CLAVE

### **stock.move vs stock.move.line**
- **stock.move**: Movimiento "planificado" o "agregado" (nivel MO)
- **stock.move.line**: Movimiento "realizado" con lotes específicos (nivel detalle)
- **Relación**: 1 `stock.move` → N `stock.move.line`

### **production_id vs raw_material_production_id**
- **production_id**: MO que **PRODUJO** este material (move de salida)
- **raw_material_production_id**: MO que **CONSUMIÓ** este material (move de entrada)
- **Uso**: Para PT usar `production_id`, para MP usar `raw_material_production_id`

### **move_raw_ids vs move_finished_ids**
- **move_raw_ids**: Materiales **CONSUMIDOS** por la MO (entradas)
- **move_finished_ids**: Productos **PRODUCIDOS** por la MO (salidas)
- **move_byproduct_ids**: Subproductos o mermas generadas

---

## 📈 PERFORMANCE Y OPTIMIZACIÓN

### **Índices Recomendados:**
```sql
CREATE INDEX idx_sml_lot ON stock_move_line(lot_id);
CREATE INDEX idx_sml_move ON stock_move_line(move_id);
CREATE INDEX idx_sml_picking ON stock_move_line(picking_id);
CREATE INDEX idx_sm_production ON stock_move(production_id);
CREATE INDEX idx_sm_raw_production ON stock_move(raw_material_production_id);
CREATE INDEX idx_mp_move_raw ON mrp_production(move_raw_ids);
CREATE INDEX idx_sp_partner ON stock_picking(partner_id);
```

### **Caché Strategy:**
```python
# Cachear MOs frecuentes (3 minutos)
cache_key = f"mo_{mo_id}"
ttl = 180

# Cachear lotes de productos populares (5 minutos)
cache_key = f"lot_{product_id}_{lot_name}"
ttl = 300

# Cachear productores (1 hora, cambian poco)
cache_key = f"partner_{partner_id}"
ttl = 3600
```

---

**📝 NOTA FINAL:**

La trazabilidad en Odoo sigue un patrón consistente:
1. Buscar el lote (`stock.lot`)
2. Encontrar sus movimientos (`stock.move.line` → `stock.move`)
3. Identificar la MO (`mrp.production`)
4. Repetir con los consumos (`move_raw_ids`)
5. Hasta llegar a `location.usage = 'supplier'` → **PRODUCTOR** ✅

**La clave es siempre: LOTE → MOVIMIENTO → MO → CONSUMOS → LOTE_ANTERIOR (recursivo)**
