# Modificación del Reporte QWeb - Fecha de OC en Factura Proveedor

## RESUMEN DE CAMBIOS

1. **Header**: Agregar "Fecha(s) OC" junto a la información de fecha
2. **Tabla de líneas**: Agregar columna "Fecha OC" por línea

## OPCIÓN 1: Herencia XML (Módulo Odoo)

Este XML se puede aplicar creando un módulo personalizado o pegándolo en Odoo Studio > Reportes > Editar.

### Archivo: `views/report_invoice_inherit.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    
    <!-- ============================================================
         HERENCIA 1: Agregar Fecha OC en sección de información (header)
         Hereda de l10n_cl.informations para facturas de Chile
    ============================================================= -->
    <template id="l10n_cl_informations_with_po_date" 
              inherit_id="l10n_cl.informations" 
              priority="99">
        
        <!-- Agregar después del bloque de Due Date -->
        <xpath expr="//div[@id='informations']/div[2]/span[contains(@t-esc,'invoice_date_due')]/.." position="after">
            
            <!-- Calcular fechas de OC -->
            <t t-set="po_orders" t-value="o.invoice_line_ids.mapped('purchase_order_id')"/>
            <t t-set="po_dates" t-value="[po.date_order for po in po_orders if po.date_order]"/>
            
            <t t-if="po_dates">
                <br/>
                <strong>Fecha(s) OC:</strong>
                <t t-if="len(set(d.date() if hasattr(d, 'date') else d for d in po_dates)) == 1">
                    <!-- Una sola fecha única -->
                    <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
                </t>
                <t t-else="">
                    <!-- Rango de fechas -->
                    <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
                    <span> - </span>
                    <span t-esc="max(po_dates)" t-options="{'widget': 'date'}"/>
                </t>
            </t>
            
        </xpath>
        
    </template>
    

    <!-- ============================================================
         HERENCIA 2: Agregar columna "Fecha OC" en tabla de líneas
         Hereda de account.report_invoice_document (template base)
    ============================================================= -->
    <template id="report_invoice_document_with_po_date_column" 
              inherit_id="account.report_invoice_document" 
              priority="99">
        
        <!-- Agregar header de columna después de Descripción -->
        <xpath expr="//table[hasclass('o_main_table')]//thead//th[@name='th_description']" position="after">
            <th name="th_po_date" class="text-start">
                <span>Fecha OC</span>
            </th>
        </xpath>
        
        <!-- Agregar celda de datos para cada línea -->
        <xpath expr="//table[hasclass('o_main_table')]//tbody//t[@t-foreach='o.invoice_line_ids.sorted(key=lambda l: (l.sequence, -l.id))']/tr/t[@t-set='current_subtotal']/../td[@name='td_name']" position="after">
            <td name="td_po_date" class="text-start">
                <t t-if="line.purchase_order_id">
                    <span t-esc="line.purchase_order_id.date_order" t-options="{'widget': 'date'}"/>
                </t>
            </td>
        </xpath>
        
    </template>

</odoo>
```

---

## OPCIÓN 2: Código para aplicar directamente en Odoo Studio

Si prefieres aplicar esto desde **Odoo Studio > Vistas > Reportes**, copia el siguiente código:

### Para el HEADER (sección informaciones):

Ir a: `Ajustes > Técnico > Interfaces de usuario > Vistas` 
Buscar: `l10n_cl.informations` 
Crear nueva vista heredada con este arch:

```xml
<data inherit_id="l10n_cl.informations" priority="99">
    <xpath expr="//div[@id='informations']/div[2]" position="inside">
        
        <t t-set="po_orders" t-value="o.invoice_line_ids.mapped('purchase_order_id')"/>
        <t t-set="po_dates" t-value="[po.date_order for po in po_orders if po.date_order]"/>
        
        <t t-if="po_dates">
            <br/>
            <strong>Fecha(s) OC:</strong>
            <t t-if="len(set(str(d)[:10] for d in po_dates)) == 1">
                <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
            </t>
            <t t-else="">
                <span t-esc="min(po_dates)" t-options="{'widget': 'date'}"/>
                <span> - </span>
                <span t-esc="max(po_dates)" t-options="{'widget': 'date'}"/>
            </t>
        </t>
        
    </xpath>
</data>
```

### Para la TABLA DE LÍNEAS:

Ir a: `Ajustes > Técnico > Interfaces de usuario > Vistas`
Buscar: `account.report_invoice_document`
Crear nueva vista heredada con este arch:

```xml
<data inherit_id="account.report_invoice_document" priority="99">
    
    <!-- Columna header -->
    <xpath expr="//table//thead//th[@name='th_description']" position="after">
        <th name="th_po_date" class="text-start">Fecha OC</th>
    </xpath>
    
    <!-- Celda de datos -->
    <xpath expr="//table//tbody//td[@name='td_name']" position="after">
        <td name="td_po_date" class="text-start">
            <t t-if="line.purchase_order_id">
                <span t-esc="line.purchase_order_id.date_order" t-options="{'widget': 'date'}"/>
            </t>
        </td>
    </xpath>
    
</data>
```

---

## OPCIÓN 3: Script Python para crear las vistas automáticamente via API

Este script crea las herencias directamente en la base de datos:

```python
"""
Crear herencias QWeb para mostrar Fecha OC en factura proveedor
"""
import xmlrpc.client

# Configuración
url = 'https://riofuturo.server98c6e.oerpondemand.net'
db = 'riofuturo-master'
username = 'mvalladares@riofuturo.cl'
password = 'c0766224bec30cac071ffe43a858c9ccbd521ddd'

# Conectar
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

# ============================================================
# HERENCIA 1: Fecha OC en header (l10n_cl.informations)
# ============================================================

# Obtener ID del template base
template_info = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search',
    [[['key', '=', 'l10n_cl.informations']]]
)

if template_info:
    arch_header = '''<data inherit_id="l10n_cl.informations" priority="99">
    <xpath expr="//div[@id='informations']/div[2]" position="inside">
        
        <t t-set="po_orders" t-value="o.invoice_line_ids.mapped('purchase_order_id')"/>
        <t t-set="po_dates" t-value="[po.date_order for po in po_orders if po.date_order]"/>
        
        <t t-if="po_dates">
            <br/>
            <strong>Fecha(s) OC:</strong>
            <t t-if="len(set(str(d)[:10] for d in po_dates)) == 1">
                <span t-esc="min(po_dates)" t-options="{\'widget\': \'date\'}"/>
            </t>
            <t t-else="">
                <span t-esc="min(po_dates)" t-options="{\'widget\': \'date\'}"/>
                <span> - </span>
                <span t-esc="max(po_dates)" t-options="{\'widget\': \'date\'}"/>
            </t>
        </t>
        
    </xpath>
</data>'''

    # Crear la vista heredada
    new_view_id = models.execute_kw(db, uid, password,
        'ir.ui.view', 'create',
        [{
            'name': 'l10n_cl.informations.po_date',
            'type': 'qweb',
            'inherit_id': template_info[0],
            'arch_db': arch_header,
            'priority': 99,
            'active': True
        }]
    )
    print(f"✅ Creada herencia para header: ir.ui.view ID {new_view_id}")

# ============================================================
# HERENCIA 2: Columna Fecha OC en tabla de líneas
# ============================================================

template_doc = models.execute_kw(db, uid, password,
    'ir.ui.view', 'search',
    [[['key', '=', 'account.report_invoice_document']]]
)

if template_doc:
    arch_table = '''<data inherit_id="account.report_invoice_document" priority="99">
    
    <xpath expr="//table//thead//th[@name='th_description']" position="after">
        <th name="th_po_date" class="text-start">Fecha OC</th>
    </xpath>
    
    <xpath expr="//table//tbody//td[@name='td_name']" position="after">
        <td name="td_po_date" class="text-start">
            <t t-if="line.purchase_order_id">
                <span t-esc="line.purchase_order_id.date_order" t-options="{\'widget\': \'date\'}"/>
            </t>
        </td>
    </xpath>
    
</data>'''

    new_view_id = models.execute_kw(db, uid, password,
        'ir.ui.view', 'create',
        [{
            'name': 'account.report_invoice_document.po_date_column',
            'type': 'qweb',
            'inherit_id': template_doc[0],
            'arch_db': arch_table,
            'priority': 99,
            'active': True
        }]
    )
    print(f"✅ Creada herencia para tabla: ir.ui.view ID {new_view_id}")

print("\n✅ Herencias creadas. Regenera el PDF de una factura proveedor para ver los cambios.")
```

---

## NOTAS IMPORTANTES

1. **Solo afecta facturas CON OC vinculada**: Si la factura no viene de una OC, el campo queda vacío.

2. **Múltiples OCs**: Muestra rango (fecha más antigua - más reciente).

3. **Relación usada**: `invoice_line_ids.purchase_order_id.date_order` (confirmada via API).

4. **Rollback**: Para deshacer, desactivar o eliminar las vistas heredadas creadas.

5. **Prioridad 99**: Asegura que esta herencia se aplique después de otras.

---

## PRÓXIMOS PASOS

1. **Elegir método de aplicación** (módulo, manual en vistas, o script API)
2. **Probar en entorno de desarrollo/staging primero**
3. **Ajustar posición/estilos según necesidad**
