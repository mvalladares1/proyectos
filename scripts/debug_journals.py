"""
DEBUG: Encontrar diario Facturas de Cliente
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/backend")
from shared.odoo_client import OdooClient

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

odoo = OdooClient(USERNAME, PASSWORD)

# Buscar todos los diarios de tipo sale
journals = odoo.search_read(
    'account.journal',
    [['type', '=', 'sale']],
    ['id', 'name', 'code']
)

print("Diarios de Venta (sale):")
for j in journals:
    print(f"  ID: {j['id']} | Code: {j['code']} | Name: {j['name']}")
