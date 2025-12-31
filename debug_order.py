from backend.services.recepcion_service import get_recepciones_mp
import json
from shared.auth import get_credenciales

# Simular credenciales (reemplaza con valores reales si es necesario, 
# o asume que el backend tiene acceso)
# NOTA: Como agente, no tengo las credenciales en texto plano aquí si no las pedí,
# pero puedo intentar usar OdooClient directamente si tengo settings.

from backend.config.settings import settings
from shared.odoo_client import OdooClient

client = OdooClient(username=settings.ODOO_USER, password=settings.ODOO_PASSWORD)

name = "RF/RFP/IN/00901"
res = client.search_read("stock.picking", [("name", "=", name)], ["id", "name", "state", "scheduled_date", "x_studio_categora_de_producto", "picking_type_id", "partner_id"])

print(f"SEARCH FOR {name}:")
print(json.dumps(res, indent=4))

# También buscar sin el filtro de categoría para ver qué tiene
res_all = client.search_read("stock.picking", [("name", "=", name)], [])
print("\nALL FIELDS FOR THE PICKING:")
print(json.dumps(res_all, indent=4))
