import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(username=USERNAME, password=PASSWORD)

print("=" * 80)
print("ANÁLISIS INCREMENTAL - FILTROS DE VENTAS")
print("=" * 80)

# Test 1: SOLO diario
print("\n1️⃣ SOLO DIARIO 'Facturas de Cliente':")
t1 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t1):,}")

# Test 2: + out_invoice
print("\n2️⃣ + move_type = 'out_invoice':")
t2 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t2):,}")

# Test 3: + state posted
print("\n3️⃣ + state = 'posted':")
t3 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t3):,}")

# Test 4: + product_id existe
print("\n4️⃣ + product_id != False:")
t4 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t4):,}")

# Test 5: + categoría PRODUCTOS
print("\n5️⃣ + categoría 'PRODUCTOS':")
t5 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t5):,}")

# Test 6: + display_type product
print("\n6️⃣ + display_type = 'product':")
t6 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['display_type', '=', 'product'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t6):,}")

# Test 7: + payment_state != reversed
print("\n7️⃣ + payment_state != 'reversed':")
t7 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['display_type', '=', 'product'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t7):,}")

# Test 8: + type != service
print("\n8️⃣ + type != 'service':")
t8 = odoo.search_read(
    'account.move.line',
    [
        ['move_id.journal_id.name', '=', 'Facturas de Cliente'],
        ['move_id.move_type', '=', 'out_invoice'],
        ['move_id.state', '=', 'posted'],
        ['move_id.payment_state', '!=', 'reversed'],
        ['product_id', '!=', False],
        ['product_id.categ_id.complete_name', 'ilike', 'PRODUCTOS'],
        ['product_id.type', '!=', 'service'],
        ['display_type', '=', 'product'],
        ['date', '>=', '2022-01-01'],
        ['date', '<=', '2026-01-23']
    ],
    ['id'],
    limit=100000
)
print(f"   Líneas: {len(t8):,}")

print("\n" + "=" * 80)
print("PÉRDIDAS POR FILTRO:")
print(f"  Categoría PRODUCTOS: -{len(t4) - len(t5):,} líneas")
print(f"  display_type='product': -{len(t5) - len(t6):,} líneas")
print(f"  payment_state!='reversed': -{len(t6) - len(t7):,} líneas")
print(f"  type!='service': -{len(t7) - len(t8):,} líneas")
print(f"\nTOTAL FINAL: {len(t8):,} líneas")
print("=" * 80)
