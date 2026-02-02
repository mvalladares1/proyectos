"""
DEBUG: Full trace de Septiembre 2025 - Paso a paso
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient
from services.flujo_caja.odoo_queries import OdooQueryManager
from services.flujo_caja.agregador import AgregadorFlujo

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: FULL TRACE Sep 2025")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)
mgr = OdooQueryManager(odoo)

# Dummy clasificador
def clasificar(code):
    if code.startswith('1103'):
        return '1.1.1', False
    return None, False

meses_lista = ['2025-09']
catalogo = {"conceptos": [{"id": "1.1.1", "tipo": "LINEA", "nombre": "Test", "actividad": "OPERACION"}]}

# 1. Get bank IDs
bank_accs = odoo.search_read('account.account', [['code', '=like', '1101%']], ['id'])
bank_ids = [a['id'] for a in bank_accs]
print(f"1. Bank IDs: {len(bank_ids)}")

# 2. Get movimientos
movs, asientos_ids = mgr.get_movimientos_efectivo_periodo('2025-09-01', '2025-09-30', bank_ids)
print(f"2. Asientos: {len(asientos_ids)}")

# 3. Create agregador
agg = AgregadorFlujo(clasificar, catalogo, meses_lista)

# 4. Process grupos
grupos = mgr.get_contrapartidas_agrupadas_mensual(asientos_ids, bank_ids, 'mensual')
print(f"3. Grupos total: {len(grupos)}")

# Procesar grupos
def parse_fn(v):
    # "septiembre 2025" -> "2025-09"
    meses_map = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06',
                 'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
    parts = v.lower().split()
    if len(parts) == 2 and parts[0] in meses_map:
        return f"{parts[1]}-{meses_map[parts[0]]}"
    return v

cuentas_monitoreadas = ['11030101']
agg.procesar_grupos_contrapartida(grupos, cuentas_monitoreadas, parse_fn)

# Check state after grupos
montos, cuentas = agg.obtener_resultados()
print(f"\n4. POST GRUPOS:")
print(f"   1.1.1: {montos.get('1.1.1', {})}")
if '1.1.1' in cuentas and '11030101' in cuentas['1.1.1']:
    print(f"   11030101 monto: ${cuentas['1.1.1']['11030101']['monto']:,.0f}")

# 5. Get etiquetas
print("\n5. Llamando get_etiquetas_por_mes...")
account_ids_to_query = []
for concepto_id, cuentas_dict in cuentas.items():
    for codigo, cuenta_data in cuentas_dict.items():
        if cuenta_data.get('account_id'):
            account_ids_to_query.append(cuenta_data['account_id'])

print(f"   Account IDs to query: {account_ids_to_query}")

etiquetas = mgr.get_etiquetas_por_mes(asientos_ids, account_ids_to_query, 'mensual')
print(f"   Etiquetas result: {len(etiquetas)}")

# Verificar si etiquetas tiene CxC
cxc_etiq = [e for e in etiquetas if e.get('account_id') and '11030101' in str(e.get('account_id'))]
print(f"   Etiquetas CxC: {len(cxc_etiq)}")

total_etiq_bal = sum(e.get('balance', 0) for e in cxc_etiq)
print(f"   Total balance etiquetas CxC: ${total_etiq_bal:,.0f}")

# Process etiquetas
agg.procesar_etiquetas(etiquetas, parse_fn)

# Check state after etiquetas
montos2, cuentas2 = agg.obtener_resultados()
print(f"\n6. POST ETIQUETAS:")
print(f"   1.1.1: {montos2.get('1.1.1', {})}")
if '1.1.1' in cuentas2 and '11030101' in cuentas2['1.1.1']:
    print(f"   11030101 monto: ${cuentas2['1.1.1']['11030101']['monto']:,.0f}")
