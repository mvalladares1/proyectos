# Flujo Rio Futuro: Producción Multi-Cliente

## 🎯 Tu Proceso Real

### 1. Cotización y Venta
```
Cliente pide cotización
  ↓
Presupuesto: PO S00843 (Excel/Sistema)
  ↓
Se crea Sale Order en Odoo
  ├─ name: "S00843"
  ├─ origin: "PO S00843" (manual)
  ├─ partner_id: TRONADOR SAC
  └─ sale_order_line:
      ├─ Producto X: 2000 kg
      └─ price_unit: $XX
```

### 2. Planificación de Producción
```
Excel/Planificación
  ↓
Se crea mrp.production en Odoo
  ├─ name: "WH/Transf/00779"
  ├─ product_id: Producto X
  ├─ origin: "PO S00843" (manual)
  └─ x_studio_po_asociada_1: → sale_order(S00843)
```

### 3. Producción (El Problema)
```
ESCENARIO REAL:
┌─────────────────────────────────────────────┐
│ ODF WH/Transf/00779                         │
│ Producción CONTINUA                         │
│                                             │
│ 09:00 ─────── 11:30 ─────── 16:00         │
│   │             │             │            │
│ Cliente A    Cambio a     Cliente B        │
│ (S00843)     Cliente B    (S00912)         │
│ 2000 kg      (sin parar)  1500 kg          │
└─────────────────────────────────────────────┘

PROBLEMA EN ODOO:
mrp.production solo puede tener:
  - origin: "PO S00843"  ← Solo UNA
  - x_studio_po_asociada_1: sale_order(S00843) ← Solo UNA

Pero produjo para DOS clientes.
```

### 4. Consumos (Donde está la VERDAD)
```
HOY: Anotan en Excel
┌─────────────────────────────────────────────┐
│ Timestamp  │ Producto  │ Kg   │ Para SO    │
├────────────┼───────────┼──────┼────────────┤
│ 09:05      │ MP-A      │ 500  │ S00843     │
│ 09:20      │ MP-A      │ 500  │ S00843     │
│ 11:32      │ MP-A      │ 300  │ S00912     │← Cambió
│ 11:50      │ MP-A      │ 400  │ S00912     │
└─────────────────────────────────────────────┘

LUEGO: Digitan en Odoo
stock.move.line:
  ├─ production_id: mrp.production(779)
  ├─ product_id: MP-A
  ├─ qty_done: 500
  ├─ date: 2026-01-15 09:05
  └─ x_studio_so_linea: → sale_order_line(#123)
                           └─ order_id: sale_order(S00843)
```

---

## ✅ Solución: Campo Existente

### Ya tienes el campo correcto ✅
```python
stock.move.line.x_studio_so_linea
  ├─ Tipo: Many2one
  ├─ Relación: sale_order_line
  └─ Permite saber:
      consumo → so_line → sale_order → cliente
```

### Lo que falta:
1. **Asegurarse que se llena correctamente** (validar que viene del Excel)
2. **Leer con nuestra API** (código ya está hecho)
3. **Visualizar en dashboard** (código ya está hecho)

---

## 🚀 Cómo Funciona Nuestro Sistema

### 1. API lee de Odoo
```python
# GET /api/v1/produccion-reconciliacion/odf/779

# Lee stock.move.line
consumos = odoo.search_read(
    'stock.move.line',
    [['production_id', '=', 779]],
    ['date', 'qty_done', 'x_studio_so_linea']
)

# Para cada consumo:
for consumo in consumos:
    so_linea_id = consumo['x_studio_so_linea'][0]
    
    # Buscar sale_order desde sale_order_line
    so_line = odoo.search_read(
        'sale.order.line',
        [['id', '=', so_linea_id]],
        ['order_id']
    )
    
    # order_id es la Sale Order
    so_id = so_line[0]['order_id'][0]
    so_nombre = so_line[0]['order_id'][1]  # "S00843"
```

### 2. Detecta transiciones
```python
# Agrupa consumos consecutivos de misma SO
segmentos = [
    {
        'so_nombre': 'S00843',
        'inicio': '09:00',
        'fin': '11:28',
        'kg_total': 2000
    },
    {
        'so_nombre': 'S00912',  ← TRANSICIÓN DETECTADA
        'inicio': '11:30',
        'fin': '16:00',
        'kg_total': 1500
    }
]
```

### 3. Calcula eficiencias
```python
# Prorratear producción según consumo
total_consumido = 3500 kg
total_producido = 3200 kg (de mrp.production.qty_produced)

S00843:
  - Consumió: 2000 kg (57%)
  - Produjo: 3200 * 0.57 = 1824 kg
  - Eficiencia: 1824/2000 = 91.2%

S00912:
  - Consumió: 1500 kg (43%)
  - Produjo: 3200 * 0.43 = 1376 kg
  - Eficiencia: 1376/1500 = 91.7%
```

### 4. Dashboard muestra
```
╔══════════════════════════════════════════════════════╗
║  ODF WH/Transf/00779 | 3200 kg producidos           ║
╚══════════════════════════════════════════════════════╝

📊 DISTRIBUCIÓN POR CLIENTE:

┌──────────┬─────────────────┬───────────┬────────────┐
│ SO       │ Cliente         │ Kg Consm. │ Eficiencia │
├──────────┼─────────────────┼───────────┼────────────┤
│ S00843   │ TRONADOR SAC    │ 2,000     │ 91.2%      │
│ S00912   │ Cliente B       │ 1,500     │ 91.7%      │
└──────────┴─────────────────┴───────────┴────────────┘

🕒 TIMELINE:
S00843 (TRONADOR) ████████████████░░░░░░ 09:00-11:28
S00912 (Cliente B) ░░░░░░░░░░░░░░░░██████ 11:30-16:00

✅ Eficiencia global: 91.4%
```

---

## 📋 Checklist de Implementación

### ✅ Fase 1: Validación (HOY)
- [ ] Ejecutar script de validación
  ```bash
  python scripts/validar_campos_odoo.py
  ```
- [ ] Confirmar que `x_studio_so_linea` existe
- [ ] Confirmar que se está llenando en Odoo
- [ ] Encontrar una ODF de ejemplo para testear

### ⏳ Fase 2: Testing (Esta Semana)
- [ ] Elegir 3 ODFs recientes con múltiples clientes
- [ ] Ejecutar reconciliación vía API
- [ ] Validar que los resultados tengan sentido
- [ ] Ajustar si es necesario

### ⏳ Fase 3: Producción (Próxima Semana)
- [ ] Capacitar usuarios en el dashboard
- [ ] Establecer proceso:
  - Excel → Odoo (asegurar que x_studio_so_linea se llene)
  - Dashboard para análisis post-producción
- [ ] Monitorear uso

---

## 🔍 Validación Rápida

### Script para verificar una ODF
```bash
cd "c:\new\RIO FUTURO\DASHBOARD\proyectos"
python scripts/validar_campos_odoo.py
```

Este script:
1. ✅ Verifica conexión a Odoo
2. ✅ Valida campos custom en mrp.production
3. ✅ Valida x_studio_so_linea en stock.move.line
4. ✅ Lista ODFs recientes
5. ✅ Permite analizar consumos de una ODF específica

---

## 💡 Preguntas Frecuentes

### ¿Por qué x_studio_so_linea y no directamente sale_order?
Porque en Odoo:
- Una Sale Order puede tener múltiples líneas (productos)
- Cada línea tiene su propia cantidad
- Al consumir, necesitas saber "para qué línea específica"

### ¿Qué pasa si no se llena x_studio_so_linea?
- El consumo aparece como "Sin SO"
- No se puede hacer reconciliación automática
- Dashboard mostrará alerta

### ¿Puedo llenar retroactivamente?
Sí, si recuerdas o tienes en Excel:
1. Ir a stock.move.line en Odoo
2. Filtrar por production_id
3. Editar y asignar x_studio_so_linea

---

## 🎯 Siguiente Paso

**Ejecuta el script de validación:**
```bash
python scripts/validar_campos_odoo.py
```

Esto te dirá:
- ✅ Si todo está configurado correctamente
- ⚠️ Qué falta o está mal configurado
- 📊 Cómo se ven tus datos actuales

**Luego cuéntame:**
1. ¿Se encontró el campo x_studio_so_linea?
2. ¿Hay ODFs con consumos que tengan ese campo llenado?
3. ¿Los datos se ven correctos?

Con eso, pasamos a testear el dashboard completo.
