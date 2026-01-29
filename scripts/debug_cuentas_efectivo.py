"""
DEBUG: Ver quÃ© cuentas de efectivo devuelve get_cuentas_efectivo
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from services.flujo_caja.odoo_queries import OdooQueryManager
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("DEBUG: get_cuentas_efectivo")
print("=" * 70)

odoo = OdooClient(USERNAME, PASSWORD)
mgr = OdooQueryManager(odoo)

# Config default (como la usa el servicio)
config = {
    "efectivo": {
        "prefijos": ["110", "111"],
        "codigos_incluir": [],
        "codigos_excluir": []
    }
}

ids = mgr.get_cuentas_efectivo(config)
print(f"IDs encontrados: {len(ids)}")

# Ver cuentas
cuentas = odoo.search_read(
    'account.account',
    [['id', 'in', ids]],
    ['id', 'code', 'name']
)

for c in cuentas:
    if c['code'] == '11030101':
        print(f"❌ ENCONTRADO: {c['code']} {c['name']} (ID: {c['id']}) -> ERROR, no debería ser efectivo")
        found = True
        break

if not found:
    print("✅ 11030101 NO ENCONTRADO en la lista de efectivo! (Esto es correcto)")
    found_1101 = False
    for c in cuentas:
        if c['code'] == '11010205':
            print(f"✅ CONFIRMADO: 11010205 sigue en la lista (ID: {c['id']})")
            found_1101 = True
    if not found_1101:
        print("❌ 11010205 DESAPARECIO! (Esto es malo)")

print("\n" + "=" * 70)
