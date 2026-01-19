"""
Debug: Analizar cuenta 21010223 (PRESTAMOS LP BANCOS US$) en enero-marzo 2026
Por qué enero aparece en $0 cuando hay movimientos en Odoo?
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.odoo_client import OdooClient
from datetime import datetime

# Configuración
codigo_cuenta = "21010223"
fecha_inicio = "2026-01-01"
fecha_fin = "2026-03-31"

print("="*80)
print(f"DEBUG CUENTA {codigo_cuenta} - ENERO A MARZO 2026")
print("="*80)

# Conectar a Odoo
print("\n1. Conectando a Odoo...")
odoo = OdooClient(
    url="https://rio-futuro-master-11821236.dev.odoo.com",
    db="rio-futuro-master-11821236",
    username="mvalladares@riofuturo.cl",
    password="c0766224bec30cac071ffe43a858c9ccbd521ddd"
)
print("   ✓ Conectado")

# 2. Buscar la cuenta
print(f"\n2. Buscando cuenta {codigo_cuenta}...")
cuenta = odoo.search_read(
    'account.account',
    [['code', '=', codigo_cuenta]],
    ['id', 'code', 'name']
)

if not cuenta:
    print(f"   ✗ Cuenta {codigo_cuenta} no encontrada")
    sys.exit(1)

account_id = cuenta[0]['id']
print(f"   ✓ ID: {account_id}")
print(f"   ✓ Nombre: {cuenta[0]['name']}")

# 3. Buscar cuentas de efectivo
print(f"\n3. Buscando cuentas de efectivo...")
cuentas_efectivo = odoo.search_read(
    'account.account',
    [['account_type', '=', 'asset_cash']],
    ['id', 'code', 'name']
)
cuentas_efectivo_ids = [c['id'] for c in cuentas_efectivo]
print(f"   ✓ {len(cuentas_efectivo_ids)} cuentas de efectivo encontradas")

# 4. Buscar movimientos de efectivo en el periodo
print(f"\n4. Buscando movimientos de efectivo ({fecha_inicio} a {fecha_fin})...")
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

print(f"   ✓ {len(movimientos_efectivo)} líneas de efectivo")
print(f"   ✓ {len(asientos_ids)} asientos únicos")

# 5. Hacer read_group por mes para la cuenta 21010223
print(f"\n5. Ejecutando read_group por mes para cuenta {codigo_cuenta}...")
grupos = odoo.models.execute_kw(
    odoo.db, odoo.uid, odoo.password,
    'account.move.line', 'read_group',
    [[
        ['move_id', 'in', asientos_ids],
        ['account_id', '=', account_id]
    ]],
    {
        'fields': ['balance', 'debit', 'credit', 'account_id', 'date'],
        'groupby': ['date:month'],
        'lazy': False
    }
)

print(f"\n   Total grupos: {len(grupos)}")
print("\n   DETALLE POR MES:")
print("   " + "-"*76)
print(f"   {'Periodo':<20} {'Balance':<15} {'Debit':<15} {'Credit':<15}")
print("   " + "-"*76)

for grupo in grupos:
    periodo = grupo.get('date:month', 'N/A')
    balance = grupo.get('balance', 0)
    debit = grupo.get('debit', 0)
    credit = grupo.get('credit', 0)
    
    print(f"   {periodo:<20} {balance:>14,.2f} {debit:>14,.2f} {credit:>14,.2f}")

# 6. Ver líneas individuales por mes
print(f"\n6. Líneas individuales de cuenta {codigo_cuenta}:")
lineas = odoo.search_read(
    'account.move.line',
    [
        ['move_id', 'in', asientos_ids],
        ['account_id', '=', account_id]
    ],
    ['date', 'name', 'debit', 'credit', 'balance', 'move_id', 'parent_state'],
    limit=100
)

print(f"\n   Total líneas: {len(lineas)}")
print("\n   " + "-"*100)
print(f"   {'Fecha':<12} {'Estado':<8} {'Debit':>15} {'Credit':>15} {'Balance':>15} {'Nombre':<30}")
print("   " + "-"*100)

# Agrupar por mes manualmente
meses = {}
for linea in lineas:
    fecha = linea.get('date', '')
    mes = fecha[:7] if fecha else 'N/A'  # YYYY-MM
    
    if mes not in meses:
        meses[mes] = {'debit': 0, 'credit': 0, 'balance': 0, 'count': 0}
    
    meses[mes]['debit'] += linea.get('debit', 0)
    meses[mes]['credit'] += linea.get('credit', 0)
    meses[mes]['balance'] += linea.get('balance', 0)
    meses[mes]['count'] += 1
    
    nombre = linea.get('name', '')[:30]
    debit = linea.get('debit', 0)
    credit = linea.get('credit', 0)
    balance = linea.get('balance', 0)
    estado = linea.get('parent_state', 'N/A')
    
    print(f"   {fecha:<12} {estado:<8} {debit:>15,.2f} {credit:>15,.2f} {balance:>15,.2f} {nombre:<30}")

# 7. Resumen por mes
print("\n7. RESUMEN POR MES (agrupación manual):")
print("   " + "-"*76)
print(f"   {'Mes':<15} {'Líneas':<8} {'Debit':>15} {'Credit':>15} {'Balance':>15}")
print("   " + "-"*76)

for mes in sorted(meses.keys()):
    datos = meses[mes]
    print(f"   {mes:<15} {datos['count']:<8} {datos['debit']:>15,.2f} {datos['credit']:>15,.2f} {datos['balance']:>15,.2f}")

# 8. Verificar parser de meses
print("\n8. PARSEO DE PERIODOS:")
print("   Testing parser de meses Odoo...")

meses_es = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
}
meses_en = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12"
}

def parse_odoo_month(odoo_month):
    try:
        parts = odoo_month.strip().lower().split()
        if len(parts) >= 2:
            mes_nombre = parts[0]
            año = parts[1]
            mes_num = meses_es.get(mes_nombre) or meses_en.get(mes_nombre)
            if mes_num and año.isdigit():
                return f"{año}-{mes_num}"
    except:
        pass
    return None

for grupo in grupos:
    periodo_odoo = grupo.get('date:month', '')
    periodo_parseado = parse_odoo_month(periodo_odoo)
    print(f"   '{periodo_odoo}' → '{periodo_parseado}'")

print("\n" + "="*80)
print("FIN DEL DEBUG")
print("="*80)
