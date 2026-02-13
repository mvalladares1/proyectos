import sys
sys.path.insert(0, "/app")
from backend.services.proforma_ajuste_service import get_facturas_borrador

# Test sin proveedor_id (Todos)
print("=== Test SIN proveedor_id (Todos) ===")
try:
    r = get_facturas_borrador(
        "mvalladares@riofuturo.cl",
        "c0766224bec30cac071ffe43a858c9ccbd521ddd",
        fecha_desde="2026-01-13",
        fecha_hasta="2026-02-12"
    )
    print(f"Resultados: {len(r)}")
    for f in r:
        print(f"  - {f.get('nombre', 'N/A')} | {f.get('proveedor_nombre', 'N/A')} | {f.get('moneda', 'N/A')}")
except Exception as e:
    import traceback; traceback.print_exc()
    print(f"Error: {e}")

print()

# Test CON proveedor_id (Agricola Aviles)
# Primero buscar el ID del proveedor
from shared.odoo_client import OdooClient
client = OdooClient(username="mvalladares@riofuturo.cl", password="c0766224bec30cac071ffe43a858c9ccbd521ddd")
partners = client.search_read(
    "res.partner",
    [("name", "ilike", "AGRICOLA AVILES")],
    ["id", "name"],
    limit=5
)
print(f"Proveedores encontrados: {partners}")

if partners:
    pid = partners[0]["id"]
    print(f"\n=== Test CON proveedor_id={pid} ===")
    try:
        r2 = get_facturas_borrador(
            "mvalladares@riofuturo.cl",
            "c0766224bec30cac071ffe43a858c9ccbd521ddd",
            proveedor_id=pid,
            fecha_desde="2026-01-13",
            fecha_hasta="2026-02-12"
        )
        print(f"Resultados: {len(r2)}")
        for f in r2:
            print(f"  - {f.get('nombre', 'N/A')} | {f.get('proveedor_nombre', 'N/A')} | create_date={f.get('create_date', 'N/A')}")
    except Exception as e:
        print(f"Error: {e}")
