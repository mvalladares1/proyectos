"""
Debug: Analizar qué cuentas contables se usan en facturas de proveedor
"""
import sys
import os
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 140)
print("ANÁLISIS DE CUENTAS CONTABLES EN FACTURAS DE PROVEEDOR")
print("=" * 140)

odoo = OdooClient(username=USERNAME, password=PASSWORD)

# Analizar 2024 completo
fecha_desde = "2024-01-01"
fecha_hasta = "2024-10-31"

print(f"\nPeríodo: {fecha_desde} hasta {fecha_hasta}")

# Obtener TODAS las líneas de factura de proveedor (sin filtro de cuenta)
print("\n" + "─" * 140)
print("1. TODAS LAS LÍNEAS (sin filtro de cuenta)")
print("─" * 140)

lineas_todas = odoo.search_read(
    'account.move.line',
    [
        ['move_id.move_type', '=', 'in_invoice'],
        ['move_id.state', '=', 'posted'],
        ['product_id', '!=', False],
        ['date', '>=', fecha_desde],
        ['date', '<=', fecha_hasta],
        ['quantity', '>', 0],
        ['debit', '>', 0]
    ],
    ['product_id', 'quantity', 'debit', 'account_id'],
    limit=100000
)

print(f"\nTotal líneas encontradas: {len(lineas_todas)}")

# Analizar cuentas
cuentas_counter = Counter()
cuentas_detalles = {}

for linea in lineas_todas:
    account = linea.get('account_id')
    if account:
        if isinstance(account, (list, tuple)) and len(account) > 1:
            account_code = account[1].split()[0] if ' ' in account[1] else account[1]
            account_name = account[1]
        else:
            account_code = str(account)
            account_name = str(account)
        
        cuentas_counter[account_code] += 1
        
        if account_code not in cuentas_detalles:
            cuentas_detalles[account_code] = {
                'nombre': account_name,
                'kg': 0,
                'monto': 0
            }
        
        cuentas_detalles[account_code]['kg'] += linea.get('quantity', 0)
        cuentas_detalles[account_code]['monto'] += linea.get('debit', 0)

print(f"\n📊 DISTRIBUCIÓN POR CUENTA CONTABLE (Top 20):")
print("─" * 140)
print(f"{'Cuenta':<15} {'Nombre':<60} {'Líneas':>10} {'kg':>15} {'Monto (CLP)':>20}")
print("─" * 140)

for cuenta_code, count in cuentas_counter.most_common(20):
    detalles = cuentas_detalles[cuenta_code]
    print(f"{cuenta_code:<15} {detalles['nombre'][:58]:<60} {count:>10,} {detalles['kg']:>15,.0f} ${detalles['monto']:>19,.0f}")

# Ahora filtrar solo productos con tipo de fruta
print("\n" + "─" * 140)
print("2. SOLO PRODUCTOS CON TIPO DE FRUTA Y MANEJO")
print("─" * 140)

# Obtener productos únicos
prod_ids = list(set([l.get('product_id', [None])[0] for l in lineas_todas if l.get('product_id')]))

productos = odoo.search_read(
    'product.product',
    [['id', 'in', prod_ids]],
    ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo', 'categ_id'],
    limit=100000
)

# Filtrar productos con tipo y manejo
productos_validos = set()

for prod in productos:
    tipo = prod.get('x_studio_sub_categora')
    if isinstance(tipo, (list, tuple)) and len(tipo) > 1:
        tipo_str = tipo[1]
    elif isinstance(tipo, str) and tipo:
        tipo_str = tipo
    else:
        tipo_str = None
    
    manejo = prod.get('x_studio_categora_tipo_de_manejo')
    if isinstance(manejo, (list, tuple)) and len(manejo) > 1:
        manejo_str = manejo[1]
    elif isinstance(manejo, str) and manejo:
        manejo_str = manejo
    else:
        manejo_str = None
    
    if tipo_str and manejo_str:
        productos_validos.add(prod['id'])

print(f"\nProductos con tipo de fruta y manejo: {len(productos_validos)} de {len(productos)}")

# Filtrar líneas solo con productos válidos
cuentas_frutas = Counter()
cuentas_frutas_detalles = {}

total_kg_frutas = 0
total_monto_frutas = 0

for linea in lineas_todas:
    prod_id = linea.get('product_id', [None])[0]
    if prod_id in productos_validos:
        account = linea.get('account_id')
        if account:
            if isinstance(account, (list, tuple)) and len(account) > 1:
                account_code = account[1].split()[0] if ' ' in account[1] else account[1]
                account_name = account[1]
            else:
                account_code = str(account)
                account_name = str(account)
            
            cuentas_frutas[account_code] += 1
            
            if account_code not in cuentas_frutas_detalles:
                cuentas_frutas_detalles[account_code] = {
                    'nombre': account_name,
                    'kg': 0,
                    'monto': 0
                }
            
            kg = linea.get('quantity', 0)
            monto = linea.get('debit', 0)
            
            cuentas_frutas_detalles[account_code]['kg'] += kg
            cuentas_frutas_detalles[account_code]['monto'] += monto
            
            total_kg_frutas += kg
            total_monto_frutas += monto

print(f"\n📊 CUENTAS USADAS PARA PRODUCTOS CON TIPO/MANEJO:")
print("─" * 140)
print(f"{'Cuenta':<15} {'Nombre':<60} {'Líneas':>10} {'kg':>15} {'Monto (CLP)':>20}")
print("─" * 140)

for cuenta_code, count in cuentas_frutas.most_common():
    detalles = cuentas_frutas_detalles[cuenta_code]
    print(f"{cuenta_code:<15} {detalles['nombre'][:58]:<60} {count:>10,} {detalles['kg']:>15,.0f} ${detalles['monto']:>19,.0f}")

print("─" * 140)
print(f"{'TOTAL':<15} {'':<60} {sum(cuentas_frutas.values()):>10,} {total_kg_frutas:>15,.0f} ${total_monto_frutas:>19,.0f}")

print(f"\n{'=' * 140}")
print("CONCLUSIÓN")
print("=" * 140)
print(f"""
Total de compras de frutas (productos con tipo/manejo):
  - Kilogramos: {total_kg_frutas:,.0f} kg
  - Monto: ${total_monto_frutas:,.0f}
  - Precio promedio: ${total_monto_frutas/total_kg_frutas:,.2f}/kg

El filtro actual usa: account_id.code =like '21%'
Debería usar las cuentas encontradas arriba.
""")
