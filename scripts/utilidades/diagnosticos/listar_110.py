import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

odoo = OdooClient("mvalladares@riofuturo.cl", "c0766224bec30cac071ffe43a858c9ccbd521ddd")
cuentas = odoo.search_read('account.account', [['code', '=like', '110%']], ['code', 'name'])
for c in sorted(cuentas, key=lambda x: x['code']):
    print(f"{c['code']} {c['name']}")
