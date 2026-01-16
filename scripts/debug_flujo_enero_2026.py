"""
Debug detallado para Flujo de Caja - Cuenta 82010102 - Enero 2026
Analiza por qué no aparecen las etiquetas correctamente.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from shared.odoo_client import OdooClient
from backend.services.flujo_caja_service import FlujoCajaService

# Credenciales
username = "mvalladares@riofuturo.cl"
password = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("="*80)
print("DEBUG DETALLADO: Cuenta 82010102 - INTERESES POR LEASING - Enero 2026")
print("="*80)

# Inicializar servicio
service = FlujoCajaService(username=username, password=password)
odoo = service.odoo

# Período
fecha_inicio = "2026-01-01"
fecha_fin = "2026-01-31"

# 1. Obtener cuentas de efectivo
cuentas_efectivo_ids = service._get_cuentas_efectivo()
print(f"\n1. Cuentas de efectivo: {len(cuentas_efectivo_ids)} cuentas")

# 2. Buscar la cuenta objetivo
cuenta_objetivo = odoo.search_read(
    'account.account',
    [['code', '=', '82010102']],
    ['id', 'code', 'name']
)
print(f"\n2. Cuenta objetivo:")
if cuenta_objetivo:
    cuenta = cuenta_objetivo[0]
    cuenta_id = cuenta['id']
    print(f"   ID: {cuenta_id}")
    print(f"   Código: {cuenta['code']}")
    print(f"   Nombre: {cuenta['name']}")
else:
    print("   ERROR: No se encontró la cuenta 82010102")
    sys.exit(1)

# 3. Buscar movimientos de efectivo en enero
movimientos_efectivo = odoo.search_read(
    'account.move.line',
    [
        ['account_id', 'in', cuentas_efectivo_ids],
        ['parent_state', 'in', ['posted', 'draft']],
        ['date', '>=', fecha_inicio],
        ['date', '<=', fecha_fin]
    ],
    ['move_id', 'date'],
    limit=10000
)

asientos_ids = list(set(
    m['move_id'][0] if isinstance(m.get('move_id'), (list, tuple)) else m.get('move_id')
    for m in movimientos_efectivo if m.get('move_id')
))

print(f"\n3. Movimientos de efectivo en enero:")
print(f"   Total asientos únicos: {len(asientos_ids)}")

# 4. Buscar TODAS las líneas de la cuenta 82010102 en esos asientos
print(f"\n4. Buscando líneas de cuenta 82010102 en los asientos de efectivo...")

contrapartidas_cuenta = odoo.search_read(
    'account.move.line',
    [
        ['move_id', 'in', asientos_ids],
        ['account_id', '=', cuenta_id]
    ],
    ['id', 'move_id', 'date', 'name', 'debit', 'credit', 'balance'],
    limit=1000
)

print(f"   Total líneas encontradas: {len(contrapartidas_cuenta)}")

if contrapartidas_cuenta:
    print(f"\n   Detalle de las líneas:")
    for i, linea in enumerate(contrapartidas_cuenta[:10], 1):
        print(f"   [{i}] Línea ID: {linea['id']}")
        print(f"       Move ID: {linea.get('move_id')}")
        print(f"       Fecha: {linea.get('date')}")
        print(f"       Etiqueta (name): '{linea.get('name')}'")
        print(f"       Débito: {linea.get('debit', 0):,.2f}")
        print(f"       Crédito: {linea.get('credit', 0):,.2f}")
        print(f"       Balance: {linea.get('balance', 0):,.2f}")
        print()

# 5. Verificar read_group por etiqueta
print(f"\n5. Probando read_group por etiqueta (sin filtro de mes)...")

try:
    grupos = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'account.move.line', 'read_group',
        [[
            ['move_id', 'in', asientos_ids],
            ['account_id', '=', cuenta_id]
        ]],
        {
            'fields': ['balance', 'name'],
            'groupby': ['name'],
            'lazy': False
        }
    )
    
    print(f"   Grupos encontrados: {len(grupos)}")
    for i, grupo in enumerate(grupos, 1):
        print(f"   [{i}] Etiqueta: '{grupo.get('name')}'")
        print(f"       Balance: {grupo.get('balance', 0):,.2f}")
        print(f"       Registros: {grupo.get('name_count', 0)}")
        print()
        
except Exception as e:
    print(f"   ERROR en read_group: {e}")

# 6. Verificar read_group por etiqueta Y mes
print(f"\n6. Probando read_group por etiqueta + mes...")

try:
    grupos_mes = odoo.models.execute_kw(
        odoo.db, odoo.uid, odoo.password,
        'account.move.line', 'read_group',
        [[
            ['move_id', 'in', asientos_ids],
            ['account_id', '=', cuenta_id]
        ]],
        {
            'fields': ['balance', 'name', 'date'],
            'groupby': ['name', 'date:month'],
            'lazy': False
        }
    )
    
    print(f"   Grupos encontrados: {len(grupos_mes)}")
    for i, grupo in enumerate(grupos_mes, 1):
        print(f"   [{i}] Etiqueta: '{grupo.get('name')}'")
        print(f"       Mes: {grupo.get('date:month')}")
        print(f"       Balance: {grupo.get('balance', 0):,.2f}")
        print()
        
except Exception as e:
    print(f"   ERROR en read_group con mes: {e}")

# 7. Verificar si hay duplicados por diferencias en el campo 'name'
print(f"\n7. Análisis de posibles duplicados en etiquetas...")

if contrapartidas_cuenta:
    etiquetas = {}
    for linea in contrapartidas_cuenta:
        nombre = linea.get('name', '')
        if nombre not in etiquetas:
            etiquetas[nombre] = []
        etiquetas[nombre].append(linea)
    
    print(f"   Etiquetas únicas: {len(etiquetas)}")
    for etiqueta, lineas in etiquetas.items():
        print(f"   '{etiqueta}': {len(lineas)} líneas")
        total_balance = sum(l.get('balance', 0) for l in lineas)
        print(f"       Balance total: {total_balance:,.2f}")

print("\n" + "="*80)
print("FIN DEBUG DETALLADO")
print("="*80)
