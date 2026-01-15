from shared.odoo_client import OdooClient
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("ODOO_USER")
password = os.getenv("ODOO_PASSWORD")

if not username or not password:
    print("⚠️ No hay credenciales en .env")
    print("Por favor, ejecuta este script desde el dashboard con credenciales válidas")
else:
    client = OdooClient(username=username, password=password)
    
    # Buscar todos los picking types de recepciones MP
    pts = client.search_read(
        "stock.picking.type",
        [("name", "ilike", "Recepciones MP")],
        ["id", "name", "warehouse_id"]
    )
    
    print("\n" + "="*60)
    print("PICKING TYPES DE RECEPCIONES MP")
    print("="*60)
    for pt in pts:
        print(f"ID: {pt['id']:3d} | {pt['name']}")
    print("="*60 + "\n")
