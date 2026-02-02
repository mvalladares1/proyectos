"""
DEBUG: Septiembre 2025 - Verifica queries directamente
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient
from services.flujo_caja.odoo_queries import OdooQueryManager

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: Verificar Query con Filtro CxC")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)
mgr = OdooQueryManager(odoo)

# Obtener cuentas banco
bank_accs = odoo.search_read('account.account', [['code', '=like', '1101%']], ['id'])
bank_ids = [a['id'] for a in bank_accs]
print(f"Bank IDs: {len(bank_ids)}")

# Obtener movimientos efectivo periodo (Septiembre 2025)
movs, asientos_ids = mgr.get_movimientos_efectivo_periodo('2025-09-01', '2025-09-30', bank_ids)
print(f"Movimientos: {len(movs)}")
print(f"Asientos IDs: {len(asientos_ids)}")

# Obtener contrapartidas agrupadas mensual
print("\nLlamando get_contrapartidas_agrupadas_mensual...")
grupos = mgr.get_contrapartidas_agrupadas_mensual(asientos_ids, bank_ids, 'mensual')
print(f"Total grupos: {len(grupos)}")

# Filtrar solo 11030101
cxc_grupos = [g for g in grupos if g.get('account_id') and '11030101' in str(g.get('account_id'))]
print(f"Grupos CxC (11030101): {len(cxc_grupos)}")

total_cxc = sum(g.get('balance', 0) for g in cxc_grupos)
print(f"Total Balance CxC: ${total_cxc:,.0f}")

# Ver algunos ejemplos
print("\nPrimeros 5 grupos CxC:")
for g in cxc_grupos[:5]:
    print(f"  {g.get('date:month')}: ${g.get('balance', 0):,.0f}")
