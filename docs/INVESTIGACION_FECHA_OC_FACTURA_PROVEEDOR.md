# Investigación: Fecha de OC en Factura de Proveedor

## FASE 1 — INVESTIGACIÓN (COMPLETADA)

### 1. Modelo exacto del documento

| Campo | Valor |
|-------|-------|
| **Modelo** | `account.move` |
| **move_type** | `in_invoice` (factura de proveedor) |
| **invoice_date** | Fecha de la factura (puede ser False en borradores) |
| **date** | Fecha contable del asiento |
| **invoice_origin** | String con nombres de OCs separados por coma (ej: "OC11477, OC12683, OC10909") |
| **state** | `draft`, `posted`, `cancel` |

### 2. Vinculación Factura Proveedor ↔ Orden de Compra

**Hallazgo crítico:** El campo `purchase_id` en `account.move` está **SIEMPRE EN FALSE**, incluso para facturas con una sola OC.

**Relación real confirmada via API:**

```
account.move
└── invoice_line_ids (One2many → account.move.line)
    └── purchase_order_id (Many2one → purchase.order)  ✅ FUNCIONA
    └── purchase_line_id (Many2one → purchase.order.line)
        └── order_id (Many2one → purchase.order)
```

**Campo disponible en account.move:**
- `purchase_order_count` (integer) - Cuenta correcta de OCs vinculadas

### 3. Datos de Órdenes de Compra vinculadas

Ejemplo de factura FAC 000826 con 19 OCs:

| OC | date_order | date_approve |
|----|------------|--------------|
| OC12670 | 2026-01-02 | 2026-02-20 |
| OC12680 | 2026-01-05 | 2026-02-20 |
| OC11419 | 2026-01-15 | 2026-02-20 |
| ... (19 OCs con fechas entre 2026-01-02 y 2026-01-15) |

### 4. Evaluación de fechas disponibles

| Campo | Modelo | Descripción |
|-------|--------|-------------|
| `invoice_date` | account.move | Fecha del documento fiscal de la factura |
| `date` | account.move | Fecha contable del asiento |
| `date_order` | purchase.order | **Fecha de CREACIÓN de la OC** ← La "Fecha de OC" buscada |
| `date_approve` | purchase.order | Fecha de aprobación/confirmación de la OC |
| `date_planned` | purchase.order.line | Fecha planificada de entrega (por línea) |

---

## FASE 2 — ANÁLISIS

### Fuente correcta para "Fecha OC"

**Campo:** `purchase.order.date_order`

**Justificación técnica:**
- Es la fecha de creación de la orden de compra
- Representa el momento en que se generó la solicitud de compra
- Es el dato que típicamente se muestra en reportes como "Fecha OC" o "Fecha de Orden"

### Caso crítico: Múltiples Órdenes de Compra

**Hallazgo importante:** Las facturas de proveedor frecuentemente consolidan múltiples OCs:
- FAC 000826: 19 OCs (rango de fechas: 2026-01-02 a 2026-01-15)
- FAC 000811: 27 OCs

**Implicaciones:**
1. **No existe una única "Fecha de OC"** para la factura completa
2. Cada línea de factura tiene su propia OC con su fecha
3. Se debe decidir qué mostrar:
   - **Opción A:** Fecha por línea (la más precisa)
   - **Opción B:** Rango de fechas (Fecha OC: 02/01 - 15/01)
   - **Opción C:** Fecha más antigua (primera OC)
   - **Opción D:** Fecha más reciente (última OC)

### Caso: Facturas parciales

Una OC puede generar múltiples facturas (entregas parciales). Cada factura parcial mantiene la referencia a la misma OC original, por lo que `date_order` sigue siendo válido.

---

## FASE 3 — PROPUESTA TÉCNICA

### Evaluación de opciones

| Opción | Pros | Contras |
|--------|------|---------|
| **A) Campo computado en account.move** | Centralizado, reutilizable, accesible en QWeb | Requiere desarrollo Python, deploy |
| **B) Lógica directa en QWeb** | Sin cambios backend, rápido de implementar | Repetitivo, difícil de mantener |
| **C) Campo related en account.move.line** | Ya existe `purchase_order_id.date_order` | Solo a nivel línea, no cabecera |

### Recomendación: **OPCIÓN B - Lógica en QWeb** (con iteración por línea)

**Razón:** 
- El campo `purchase_id` está en False y no es confiable
- La relación real es via `invoice_line_ids.purchase_order_id`
- Para mostrar la fecha de OC **por línea**, es directo en QWeb
- Si se necesita la fecha en cabecera, mostrar rango o lista de fechas únicas

---

### SNIPPETS RECOMENDADOS

#### 1. Mostrar Fecha de OC POR LÍNEA en el detalle de productos

```xml
<!-- En el template QWeb de la factura proveedor -->
<!-- Agregar columna "Fecha OC" en la tabla de líneas -->

<t t-foreach="o.invoice_line_ids.filtered(lambda l: l.display_type not in ('line_section', 'line_note'))" t-as="line">
    <tr>
        <!-- Columnas existentes... -->
        <td>
            <t t-if="line.purchase_order_id">
                <span t-field="line.purchase_order_id.date_order" t-options="{'widget': 'date'}"/>
            </t>
        </td>
        <!-- Resto de columnas... -->
    </tr>
</t>
```

#### 2. Mostrar RANGO de fechas en cabecera (si hay múltiples OCs)

```xml
<!-- Antes de la tabla de líneas o en cabecera del reporte -->
<t t-set="purchase_orders" t-value="o.invoice_line_ids.mapped('purchase_order_id')"/>
<t t-set="po_dates" t-value="purchase_orders.mapped('date_order')"/>

<t t-if="po_dates">
    <div class="row">
        <div class="col-6">
            <strong>Fecha(s) de OC:</strong>
            <t t-if="len(set(po_dates)) == 1">
                <!-- Una sola fecha -->
                <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
            </t>
            <t t-else="">
                <!-- Rango de fechas -->
                <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
                <span> - </span>
                <span t-esc="max(po_dates)" t-options="{'widget': 'date'}"/>
            </t>
        </div>
    </div>
</t>
```

#### 3. Mostrar todas las OCs con sus fechas (lista detallada)

```xml
<t t-set="purchase_orders" t-value="o.invoice_line_ids.mapped('purchase_order_id')"/>
<t t-if="purchase_orders">
    <div class="po-dates-list">
        <strong>Órdenes de Compra:</strong>
        <ul>
            <t t-foreach="purchase_orders.sorted(key=lambda x: x.date_order)" t-as="po">
                <li>
                    <span t-field="po.name"/> - 
                    <span t-field="po.date_order" t-options="{'widget': 'date'}"/>
                </li>
            </t>
        </ul>
    </div>
</t>
```

---

### ALTERNATIVA: Campo computado en Python (si se necesita en cabecera)

Si se requiere un campo reutilizable para filtros/reportes/API:

```python
# En un módulo personalizado

from odoo import models, fields, api

class AccountMove(models.Model):
    _inherit = 'account.move'
    
    x_po_date_min = fields.Datetime(
        string="Fecha OC (Más antigua)",
        compute="_compute_po_dates",
        store=True,
    )
    
    x_po_date_max = fields.Datetime(
        string="Fecha OC (Más reciente)", 
        compute="_compute_po_dates",
        store=True,
    )
    
    @api.depends('invoice_line_ids.purchase_order_id.date_order')
    def _compute_po_dates(self):
        for move in self:
            po_dates = move.invoice_line_ids.mapped('purchase_order_id.date_order')
            po_dates = [d for d in po_dates if d]  # Filtrar False/None
            
            move.x_po_date_min = min(po_dates) if po_dates else False
            move.x_po_date_max = max(po_dates) if po_dates else False
```

**Impacto en rendimiento:** Bajo. El cómputo solo se ejecuta al crear/modificar líneas de factura.

---

### Casos borde considerados

| Caso | Comportamiento |
|------|----------------|
| Factura sin OC (creada manual) | `purchase_order_id` = False, campo vacío |
| Factura con 1 OC | Muestra fecha única |
| Factura con múltiples OCs | Muestra rango o lista según implementación |
| OC en borrador sin aprobar | `date_order` existe, `date_approve` = False |
| Factura parcial de OC | Mantiene referencia a la OC original |

---

## RESPUESTA FINAL

**Para mostrar "Fecha de OC" en el reporte de factura proveedor:**

1. **A nivel de línea:** Usar `line.purchase_order_id.date_order` (directo y preciso)
2. **A nivel de cabecera:** Mostrar rango con `min()` y `max()` de las fechas de todas las OCs vinculadas
3. **El campo `purchase_id` NO ES CONFIABLE** - siempre está en False
4. **La relación correcta es:** `invoice_line_ids.purchase_order_id.date_order`
