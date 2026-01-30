"""
Análisis completo de ventas - ¿Qué estamos excluyendo?
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from datetime import datetime

# Credenciales
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

fecha_desde = "2022-01-01"
fecha_hasta = datetime.now().strftime("%Y-%m-%d")

print("\n" + "="*120)
print("ANÁLISIS COMPLETO DE VENTAS - ¿QUÉ ESTAMOS EXCLUYENDO?")
print("="*120)

odoo = OdooClient(username=ODOO_USER, password=ODOO_PASSWORD)

# ============================================================================
# 1. TODAS las líneas de facturas de cliente (sin filtros restrictivos)
# ============================================================================
print(f"\n📊 Paso 1: TODAS las líneas del diario 'Facturas de Cliente'...\n")

lineas_base = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['product_id', '!=', False],
        ['date', '>=', fecha_desde],
        ['date', '<=', fecha_hasta]
    ],
    ['move_id', 'product_id', 'quantity', 'credit', 'debit', 'account_id', 'display_type'],
    limit=100000
)

# Obtener payment_state de las facturas
move_ids = list(set([l['move_id'][0] for l in lineas_base if l.get('move_id')]))
moves = odoo.search_read('account.move', [['id', 'in', move_ids]], ['id', 'payment_state'])
move_payment_state = {m['id']: m.get('payment_state', '') for m in moves}

print(f"Total líneas encontradas: {len(lineas_base):,}")

# Obtener productos para clasificar
prod_ids = list(set([l['product_id'][0] for l in lineas_base if l.get('product_id')]))
print(f"Productos únicos: {len(prod_ids)}")

# Obtener templates con tipo_fruta y manejo (con active_test=False)
productos = odoo.models.execute_kw(
    odoo.db, odoo.uid, odoo.password,
    'product.product', 'search_read',
    [[['id', 'in', prod_ids]]],
    {'fields': ['id', 'product_tmpl_id'], 'context': {'active_test': False}}
)

template_ids = list(set([p['product_tmpl_id'][0] for p in productos if p.get('product_tmpl_id')]))
templates = odoo.models.execute_kw(
    odoo.db, odoo.uid, odoo.password,
    'product.template', 'search_read',
    [[['id', 'in', template_ids]]],
    {'fields': ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'], 'context': {'active_test': False}}
)

# Mapear productos a templates
prod_to_template = {p['id']: p['product_tmpl_id'][0] for p in productos}
template_map = {t['id']: t for t in templates}

print(f"Templates únicos: {len(templates)}")

# ============================================================================
# 2. ANÁLISIS: ¿Cuántas tienen tipo_fruta y manejo?
# ============================================================================
print(f"\n{'='*120}")
print("CLASIFICACIÓN POR TIPO DE PRODUCTO")
print(f"{'='*120}\n")

con_tipo_manejo = []
sin_tipo_manejo = []
sin_template = []

for linea in lineas_base:
    prod_id = linea.get('product_id', [None])[0] if linea.get('product_id') else None
    template_id = prod_to_template.get(prod_id)
    template = template_map.get(template_id, {})
    
    tiene_tipo = template.get('x_studio_sub_categora') not in [None, False, '']
    tiene_manejo = template.get('x_studio_categora_tipo_de_manejo') not in [None, False, '']
    
    if template_id:
        if tiene_tipo and tiene_manejo:
            con_tipo_manejo.append(linea)
        else:
            sin_tipo_manejo.append(linea)
    else:
        sin_template.append(linea)

print(f"✅ Con tipo_fruta Y manejo: {len(con_tipo_manejo):,} líneas")
print(f"⚠️  Sin tipo_fruta o manejo: {len(sin_tipo_manejo):,} líneas")
print(f"❌ Sin template: {len(sin_template):,} líneas")

# ============================================================================
# 3. ANÁLISIS: De las que tienen tipo_fruta y manejo, ¿qué filtros aplican?
# ============================================================================
print(f"\n{'='*120}")
print(f"ANÁLISIS DE FILTROS (sobre {len(con_tipo_manejo):,} líneas con tipo_fruta y manejo)")
print(f"{'='*120}\n")

# Filtro 1: Categoría PRODUCTOS
cat_productos = []
cat_otros = []
for linea in con_tipo_manejo:
    prod_id = linea.get('product_id', [None])[0] if linea.get('product_id') else None
    template_id = prod_to_template.get(prod_id)
    template = template_map.get(template_id, {})
    categoria = template.get('categ_id', [False, ''])[1] if template.get('categ_id') else ''
    
    if 'PRODUCTOS' in categoria.upper():
        cat_productos.append(linea)
    else:
        cat_otros.append(linea)

print(f"Filtro 1 - Categoría 'PRODUCTOS':")
print(f"  ✅ Cumplen: {len(cat_productos):,}")
print(f"  ❌ Excluidas: {len(cat_otros):,}")
if len(cat_otros) > 0:
    categorias_excluidas = set()
    for linea in cat_otros[:10]:
        prod_id = linea.get('product_id', [None])[0] if linea.get('product_id') else None
        template_id = prod_to_template.get(prod_id)
        template = template_map.get(template_id, {})
        categoria = template.get('categ_id', [False, ''])[1] if template.get('categ_id') else 'Sin categoría'
        categorias_excluidas.add(categoria)
    print(f"  Categorías excluidas: {', '.join(list(categorias_excluidas)[:5])}")

# Filtro 2: Cuenta 41010101
cuenta_correcta = []
cuenta_otra = []
for linea in cat_productos:
    cuenta = linea.get('account_id', [False, ''])[1] if linea.get('account_id') else ''
    if '41010101' in cuenta:
        cuenta_correcta.append(linea)
    else:
        cuenta_otra.append(linea)

print(f"\nFiltro 2 - Cuenta '41010101':")
print(f"  ✅ Cumplen: {len(cuenta_correcta):,}")
print(f"  ❌ Excluidas: {len(cuenta_otra):,}")
if len(cuenta_otra) > 0:
    cuentas_excluidas = set([l.get('account_id', [False, ''])[1] for l in cuenta_otra[:20] if l.get('account_id')])
    print(f"  Otras cuentas: {', '.join(list(cuentas_excluidas)[:3])}")

# Filtro 3: credit > 0
con_credito = []
sin_credito = []
for linea in cuenta_correcta:
    if linea.get('credit', 0) > 0:
        con_credito.append(linea)
    else:
        sin_credito.append(linea)

print(f"\nFiltro 3 - Credit > 0:")
print(f"  ✅ Cumplen: {len(con_credito):,}")
print(f"  ❌ Excluidas: {len(sin_credito):,} (tienen débito={sum([l.get('debit',0) for l in sin_credito[:10]]):,.0f})")

# Filtro 4: display_type = 'product'
display_product = []
display_otro = []
for linea in con_credito:
    if linea.get('display_type') == 'product':
        display_product.append(linea)
    else:
        display_otro.append(linea)

print(f"\nFiltro 4 - display_type = 'product':")
print(f"  ✅ Cumplen: {len(display_product):,}")
print(f"  ❌ Excluidas: {len(display_otro):,}")
if len(display_otro) > 0:
    display_types = {}
    for linea in display_otro:
        dt = linea.get('display_type', 'None')
        display_types[dt] = display_types.get(dt, 0) + 1
    print(f"  Tipos excluidos: {display_types}")

# Filtro 5: payment_state != 'reversed'
no_revertidas = []
revertidas = []
for linea in display_product:
    move_id = linea.get('move_id', [None])[0] if linea.get('move_id') else None
    payment_state = move_payment_state.get(move_id, '')
    if payment_state != 'reversed':
        no_revertidas.append(linea)
    else:
        revertidas.append(linea)

print(f"\nFiltro 5 - payment_state != 'reversed':")
print(f"  ✅ Cumplen: {len(no_revertidas):,}")
print(f"  ❌ Excluidas: {len(revertidas):,}")

# ============================================================================
# 4. RESUMEN FINAL
# ============================================================================
print(f"\n{'='*120}")
print("RESUMEN DEL FILTRADO")
print(f"{'='*120}\n")

print(f"Líneas base (todas facturas cliente): {len(lineas_base):,}")
print(f"  └─ Con tipo_fruta y manejo: {len(con_tipo_manejo):,}")
print(f"       └─ Categoría PRODUCTOS: {len(cat_productos):,}")
print(f"            └─ Cuenta 41010101: {len(cuenta_correcta):,}")
print(f"                 └─ Credit > 0: {len(con_credito):,}")
print(f"                      └─ display_type='product': {len(display_product):,}")
print(f"                           └─ No revertidas: {len(no_revertidas):,} ✅ FINAL")

print(f"\nTotal EXCLUIDO: {len(lineas_base) - len(no_revertidas):,} líneas")
print(f"  - Sin tipo_fruta/manejo: {len(sin_tipo_manejo) + len(sin_template):,}")
print(f"  - Categoría != PRODUCTOS: {len(cat_otros):,}")
print(f"  - Cuenta != 41010101: {len(cuenta_otra):,}")
print(f"  - Sin crédito: {len(sin_credito):,}")
print(f"  - display_type != product: {len(display_otro):,}")
print(f"  - Revertidas: {len(revertidas):,}")

# ============================================================================
# 5. PROPUESTA: ¿Qué pasa si SOLO filtramos por tipo_fruta/manejo?
# ============================================================================
print(f"\n{'='*120}")
print("PROPUESTA: SOLO tipo_fruta y manejo (sin otros filtros)")
print(f"{'='*120}\n")

# Calcular totales
total_kg = sum([l.get('quantity', 0) for l in con_tipo_manejo])
total_monto = sum([l.get('credit', 0) - l.get('debit', 0) for l in con_tipo_manejo])

print(f"Líneas: {len(con_tipo_manejo):,}")
print(f"Total kg: {total_kg:,.2f}")
print(f"Total $: ${total_monto:,.0f}")

print(f"\nCon TODOS los filtros actuales:")
total_kg_filtrado = sum([l.get('quantity', 0) for l in no_revertidas])
total_monto_filtrado = sum([l.get('credit', 0) for l in no_revertidas])
print(f"Líneas: {len(no_revertidas):,}")
print(f"Total kg: {total_kg_filtrado:,.2f}")
print(f"Total $: ${total_monto_filtrado:,.0f}")

print(f"\nDIFERENCIA:")
print(f"Líneas: {len(con_tipo_manejo) - len(no_revertidas):,}")
print(f"Kg: {total_kg - total_kg_filtrado:,.2f}")
print(f"$: ${total_monto - total_monto_filtrado:,.0f}")

print("\n" + "="*120)
print("FIN DEL ANÁLISIS")
print("="*120)
