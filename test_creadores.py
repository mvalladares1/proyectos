import sys
sys.path.insert(0, "/app")
from shared.odoo_client import OdooClient

client = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")

# Buscar TODAS las facturas borrador sin filtro de usuario
domain = [
    ("move_type", "=", "in_invoice"),
    ("state", "=", "draft"),
    ("create_date", ">=", "2026-01-13"),
    ("create_date", "<=", "2026-02-12 23:59:59"),
]

facturas = client.search_read(
    "account.move",
    domain,
    ["id", "name", "partner_id", "currency_id", "create_uid", "amount_total"],
    limit=100,
    order="create_date desc"
)

print(f"Total facturas borrador encontradas: {len(facturas)}")
print()

# Agrupar por creador
creadores = {}
for f in facturas:
    creador = f.get("create_uid", [0, "Desconocido"])
    nombre_creador = creador[1] if isinstance(creador, (list, tuple)) and len(creador) > 1 else str(creador)
    partner = f.get("partner_id", [0, ""])
    partner_name = partner[1] if isinstance(partner, (list, tuple)) and len(partner) > 1 else str(partner)
    currency = f.get("currency_id", [0, ""])
    currency_name = currency[1] if isinstance(currency, (list, tuple)) and len(currency) > 1 else str(currency)
    
    if nombre_creador not in creadores:
        creadores[nombre_creador] = 0
    creadores[nombre_creador] += 1
    
    print(f"  {f['name']:15s} | {partner_name:45s} | {currency_name:5s} | Creador: {nombre_creador}")

print()
print("=== Resumen por creador ===")
for c, count in sorted(creadores.items(), key=lambda x: -x[1]):
    print(f"  {c}: {count} facturas")
