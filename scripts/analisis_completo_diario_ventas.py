import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from collections import defaultdict

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 100)
print("ANÁLISIS COMPLETO - DIARIO 'FACTURAS DE CLIENTE'")
print("=" * 100)

# ============================================================================
# 1. ANÁLISIS GENERAL DE FACTURAS
# ============================================================================
print("\n" + "=" * 100)
print("1️⃣  ANÁLISIS DE FACTURAS (account.move)")
print("=" * 100)

facturas = odoo.search_read(
    'account.move',
    [
        ['journal_id.name', '=', 'Facturas de Cliente'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id', 'name', 'move_type', 'state', 'payment_state', 'date', 'amount_total'],
    limit=100000
)

print(f"\n📊 Total facturas: {len(facturas):,}")

# Distribución por tipo
tipos_factura = defaultdict(int)
for f in facturas:
    tipos_factura[f.get('move_type')] += 1

print("\n📋 Por tipo de movimiento:")
for tipo, count in sorted(tipos_factura.items(), key=lambda x: -x[1]):
    print(f"   {tipo:20s}: {count:,} facturas ({count/len(facturas)*100:.1f}%)")

# Distribución por estado
estados = defaultdict(int)
for f in facturas:
    estados[f.get('state')] += 1

print("\n📋 Por estado:")
for estado, count in sorted(estados.items(), key=lambda x: -x[1]):
    print(f"   {estado:20s}: {count:,} facturas ({count/len(facturas)*100:.1f}%)")

# Distribución por payment_state
payment_states = defaultdict(int)
for f in facturas:
    ps = f.get('payment_state') or 'None'
    payment_states[ps] += 1

print("\n📋 Por estado de pago:")
for ps, count in sorted(payment_states.items(), key=lambda x: -x[1]):
    print(f"   {ps:20s}: {count:,} facturas ({count/len(facturas)*100:.1f}%)")

# Totales
total_amount = sum(f.get('amount_total', 0) for f in facturas)
print(f"\n💰 Monto total: ${total_amount:,.0f}")

# ============================================================================
# 2. ANÁLISIS DE LÍNEAS (account.move.line)
# ============================================================================
print("\n" + "=" * 100)
print("2️⃣  ANÁLISIS DE LÍNEAS (account.move.line)")
print("=" * 100)

lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id', 'product_id', 'name', 'display_type', 'quantity', 'credit', 'debit', 'account_id', 'move_id'],
    limit=100000
)

print(f"\n📊 Total líneas: {len(lineas):,}")

# Por display_type
display_types = defaultdict(int)
for l in lineas:
    dt = l.get('display_type') or 'None/False'
    display_types[dt] += 1

print("\n📋 Por display_type:")
for dt, count in sorted(display_types.items(), key=lambda x: -x[1]):
    print(f"   {dt:20s}: {count:,} líneas ({count/len(lineas)*100:.1f}%)")

# Con/sin producto
con_producto = sum(1 for l in lineas if l.get('product_id'))
sin_producto = len(lineas) - con_producto

print(f"\n📋 Con/sin product_id:")
print(f"   CON producto      : {con_producto:,} líneas ({con_producto/len(lineas)*100:.1f}%)")
print(f"   SIN producto      : {sin_producto:,} líneas ({sin_producto/len(lineas)*100:.1f}%)")

# ============================================================================
# 3. ANÁLISIS DE LÍNEAS CON PRODUCTO
# ============================================================================
print("\n" + "=" * 100)
print("3️⃣  ANÁLISIS DE LÍNEAS CON PRODUCTO")
print("=" * 100)

lineas_con_producto = [l for l in lineas if l.get('product_id')]
print(f"\n📊 Líneas con producto: {len(lineas_con_producto):,}")

# Obtener productos únicos
productos_ids = list(set([l.get('product_id')[0] for l in lineas_con_producto]))
print(f"📊 Productos únicos: {len(productos_ids):,}")

# Obtener info de productos
productos = odoo.models.execute_kw(
    odoo.db, odoo.uid, odoo.password,
    'product.product', 'read',
    [productos_ids, ['id', 'name', 'categ_id', 'type', 'active', 'product_tmpl_id']],
    {'context': {'active_test': False}}
)

print(f"📊 Productos obtenidos: {len(productos):,}")

# Por categoría
categorias = defaultdict(int)
for p in productos:
    categ = p.get('categ_id', [None, 'Sin categoría'])
    categ_name = categ[1] if isinstance(categ, (list, tuple)) else str(categ)
    categorias[categ_name] += 1

print("\n📋 Por categoría de producto:")
for categ, count in sorted(categorias.items(), key=lambda x: -x[1])[:15]:
    print(f"   {categ[:50]:50s}: {count:,} productos")

# Por tipo de producto
tipos_producto = defaultdict(int)
for p in productos:
    tipos_producto[p.get('type', 'unknown')] += 1

print("\n📋 Por tipo de producto:")
for tipo, count in sorted(tipos_producto.items(), key=lambda x: -x[1]):
    print(f"   {tipo:20s}: {count:,} productos ({count/len(productos)*100:.1f}%)")

# Activos vs archivados
activos = sum(1 for p in productos if p.get('active', True))
archivados = len(productos) - activos
print(f"\n📋 Estado de productos:")
print(f"   Activos           : {activos:,} productos ({activos/len(productos)*100:.1f}%)")
print(f"   Archivados        : {archivados:,} productos ({archivados/len(productos)*100:.1f}%)")

# ============================================================================
# 4. ANÁLISIS DE TIPO_FRUTA Y MANEJO
# ============================================================================
print("\n" + "=" * 100)
print("4️⃣  ANÁLISIS DE TIPO_FRUTA Y MANEJO")
print("=" * 100)

# Obtener templates
template_ids = list(set([p.get('product_tmpl_id')[0] for p in productos if p.get('product_tmpl_id')]))
print(f"\n📊 Templates únicos: {len(template_ids):,}")

templates = odoo.models.execute_kw(
    odoo.db, odoo.uid, odoo.password,
    'product.template', 'read',
    [template_ids, ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo']],
    {'context': {'active_test': False}}
)

print(f"📊 Templates obtenidos: {len(templates):,}")

# Analizar tipo_fruta
con_tipo_fruta = 0
sin_tipo_fruta = 0
tipos_fruta = defaultdict(int)

for t in templates:
    tipo = t.get('x_studio_sub_categora')
    if tipo:
        con_tipo_fruta += 1
        tipo_str = tipo[1] if isinstance(tipo, (list, tuple)) and len(tipo) > 1 else str(tipo)
        tipos_fruta[tipo_str] += 1
    else:
        sin_tipo_fruta += 1

print(f"\n📋 Tipo de Fruta:")
print(f"   CON tipo_fruta    : {con_tipo_fruta:,} templates ({con_tipo_fruta/len(templates)*100:.1f}%)")
print(f"   SIN tipo_fruta    : {sin_tipo_fruta:,} templates ({sin_tipo_fruta/len(templates)*100:.1f}%)")

print("\n📋 Distribución de tipos de fruta:")
for tipo, count in sorted(tipos_fruta.items(), key=lambda x: -x[1])[:10]:
    print(f"   {tipo[:30]:30s}: {count:,} templates")

# Analizar manejo
con_manejo = 0
sin_manejo = 0
manejos = defaultdict(int)

for t in templates:
    manejo = t.get('x_studio_categora_tipo_de_manejo')
    if manejo:
        con_manejo += 1
        manejo_str = manejo[1] if isinstance(manejo, (list, tuple)) and len(manejo) > 1 else str(manejo)
        manejos[manejo_str] += 1
    else:
        sin_manejo += 1

print(f"\n📋 Manejo:")
print(f"   CON manejo        : {con_manejo:,} templates ({con_manejo/len(templates)*100:.1f}%)")
print(f"   SIN manejo        : {sin_manejo:,} templates ({sin_manejo/len(templates)*100:.1f}%)")

print("\n📋 Distribución de manejos:")
for manejo, count in sorted(manejos.items(), key=lambda x: -x[1])[:10]:
    print(f"   {manejo[:30]:30s}: {count:,} templates")

# Con ambos
con_ambos = sum(1 for t in templates 
                if t.get('x_studio_sub_categora') and t.get('x_studio_categora_tipo_de_manejo'))
print(f"\n📋 Con AMBOS (tipo_fruta Y manejo):")
print(f"   {con_ambos:,} templates ({con_ambos/len(templates)*100:.1f}%)")

# ============================================================================
# 5. ANÁLISIS DE CUENTAS CONTABLES
# ============================================================================
print("\n" + "=" * 100)
print("5️⃣  ANÁLISIS DE CUENTAS CONTABLES")
print("=" * 100)

cuentas = defaultdict(int)
for l in lineas:
    cuenta = l.get('account_id', [None, 'Sin cuenta'])
    cuenta_name = cuenta[1] if isinstance(cuenta, (list, tuple)) else str(cuenta)
    cuentas[cuenta_name] += 1

print(f"\n📋 Top 15 cuentas más usadas:")
for cuenta, count in sorted(cuentas.items(), key=lambda x: -x[1])[:15]:
    print(f"   {cuenta[:60]:60s}: {count:,} líneas")

# ============================================================================
# 6. ANÁLISIS ESPECÍFICO PARA STOCK TEÓRICO
# ============================================================================
print("\n" + "=" * 100)
print("6️⃣  FILTROS PARA STOCK TEÓRICO - ANÁLISIS CASCADA")
print("=" * 100)

print("\n🔍 Aplicando filtros paso a paso:")

# Base: todas las líneas
print(f"\n   Base (todas las líneas)         : {len(lineas):,}")

# Filtro 1: out_invoice
lineas_f1 = [l for l in lineas if odoo.search_read('account.move', [['id', '=', l.get('move_id')[0]]], ['move_type'], limit=1)[0].get('move_type') == 'out_invoice']
print(f"   + move_type='out_invoice'       : {len(lineas_f1):,} (-{len(lineas)-len(lineas_f1):,})")

# Esto es demasiado lento, mejor hacer consultas específicas
print("\n   Usando consultas optimizadas...\n")

# Test completo con filtros
test_base = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id'],
    limit=100000
)
print(f"   1. Base diario                          : {len(test_base):,}")

test_out = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id'],
    limit=100000
)
print(f"   2. + out_invoice                        : {len(test_out):,} (-{len(test_base)-len(test_out):,})")

test_posted = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id'],
    limit=100000
)
print(f"   3. + state='posted'                     : {len(test_posted):,} (-{len(test_out)-len(test_posted):,})")

test_not_reversed = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id'],
    limit=100000
)
print(f"   4. + payment_state!='reversed'          : {len(test_not_reversed):,} (-{len(test_posted)-len(test_not_reversed):,})")

test_display = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['display_type', '=', 'product'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id'],
    limit=100000
)
print(f"   5. + display_type='product'             : {len(test_display):,} (-{len(test_not_reversed)-len(test_display):,})")
print(f"      ⚠️  Líneas COGS excluidas             : {len(test_not_reversed)-len(test_display):,}")

# ============================================================================
# 7. PROBLEMAS POTENCIALES
# ============================================================================
print("\n" + "=" * 100)
print("7️⃣  PROBLEMAS POTENCIALES DETECTADOS")
print("=" * 100)

problemas = []

# Líneas sin producto con display_type='product'
lineas_sin_prod_display = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['display_type', '=', 'product'],
        ['product_id', '=', False],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-26']
    ],
    ['id', 'name', 'move_id'],
    limit=1000
)

if lineas_sin_prod_display:
    print(f"\n⚠️  PROBLEMA 1: Líneas display_type='product' SIN product_id")
    print(f"   Cantidad: {len(lineas_sin_prod_display):,} líneas")
    print(f"   Descripción: Facturas con texto libre (no vinculadas a producto)")
    print(f"   Solución: Ahora SE INCLUYEN en el análisis")
    print(f"\n   Ejemplos:")
    for i, l in enumerate(lineas_sin_prod_display[:5], 1):
        move_name = l.get('move_id', [None, 'N/A'])[1]
        print(f"      {i}. {move_name}: {l.get('name', 'N/A')[:60]}")

# Facturas revertidas
facturas_revertidas = [f for f in facturas if f.get('payment_state') == 'reversed']
if facturas_revertidas:
    print(f"\n⚠️  PROBLEMA 2: Facturas revertidas")
    print(f"   Cantidad: {len(facturas_revertidas):,} facturas")
    print(f"   Descripción: Facturas que fueron anuladas/revertidas")
    print(f"   Solución: EXCLUIDAS con filtro payment_state != 'reversed'")
    total_revertido = sum(f.get('amount_total', 0) for f in facturas_revertidas)
    print(f"   Monto total: ${total_revertido:,.0f}")

# Productos sin tipo_fruta o manejo
productos_sin_ambos = len(templates) - con_ambos
if productos_sin_ambos > 0:
    print(f"\n⚠️  PROBLEMA 3: Templates sin tipo_fruta Y/O manejo")
    print(f"   Cantidad: {productos_sin_ambos:,} templates ({productos_sin_ambos/len(templates)*100:.1f}%)")
    print(f"   - Sin tipo_fruta: {sin_tipo_fruta:,}")
    print(f"   - Sin manejo: {sin_manejo:,}")
    print(f"   Descripción: Productos que NO se pueden agrupar correctamente")
    print(f"   Solución: Se marcan como 'Sin tipo' / 'Sin manejo' en reportes")

print("\n" + "=" * 100)
print("RESUMEN FINAL")
print("=" * 100)

print(f"\n📊 DATOS GENERALES:")
print(f"   Facturas totales          : {len(facturas):,}")
print(f"   Líneas totales            : {len(lineas):,}")
print(f"   Productos únicos          : {len(productos):,}")
print(f"   Templates únicos          : {len(templates):,}")

print(f"\n📊 FILTRADO PARA STOCK TEÓRICO:")
print(f"   Líneas base (diario)      : {len(test_base):,}")
print(f"   Líneas válidas (filtros)  : {len(test_display):,}")
print(f"   Exclusión COGS            : {len(test_not_reversed)-len(test_display):,} ({(len(test_not_reversed)-len(test_display))/len(test_base)*100:.1f}%)")
print(f"   Exclusión revertidas      : {len(test_posted)-len(test_not_reversed):,}")

print(f"\n📊 CALIDAD DE DATOS:")
print(f"   Templates con tipo+manejo : {con_ambos:,}/{len(templates):,} ({con_ambos/len(templates)*100:.1f}%)")
print(f"   Productos archivados      : {archivados:,}/{len(productos):,} ({archivados/len(productos)*100:.1f}%)")
print(f"   Líneas texto libre        : {len(lineas_sin_prod_display):,}")

print("\n" + "=" * 100)
