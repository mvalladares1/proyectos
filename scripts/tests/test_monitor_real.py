"""Test para verificar datos reales del monitor con lógica corregida"""
from shared.odoo_client import OdooClient

odoo = OdooClient(
    username='mvalladares@riofuturo.cl', 
    password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
)

# TODOS los procesos pendientes (no done, no cancel)
# Estados pendientes: progress, to_close, confirmed, draft
domain = [['state', 'not in', ['done', 'cancel']]]
ordenes = odoo.search_read(
    'mrp.production', 
    domain, 
    ['name', 'product_qty', 'qty_produced', 'state', 'x_studio_sala_de_proceso', 
     'x_studio_inicio_de_proceso', 'product_id'], 
    limit=500
)

kg_total = sum(o.get('product_qty', 0) or 0 for o in ordenes)
print(f"=== PROCESOS PENDIENTES ===")
print(f"Total: {len(ordenes)}")
print(f"KG Programados: {kg_total:,.2f}")

# Por estado
estados = {}
for o in ordenes:
    st = o.get('state', 'unknown')
    estados[st] = estados.get(st, 0) + 1
print(f"Estados: {estados}")

# Por planta (según sala)
plantas = {"RIO FUTURO": 0, "VILKUN": 0, "SAN JOSE": 0}
for o in ordenes:
    sala = str(o.get('x_studio_sala_de_proceso', '') or '').upper()
    if 'VILKUN' in sala or 'VLK' in sala:
        plantas["VILKUN"] += 1
    elif 'SAN JOSE' in sala or 'SAN JOSÉ' in sala:
        plantas["SAN JOSE"] += 1
    else:
        plantas["RIO FUTURO"] += 1
print(f"Por Planta: {plantas}")

# Mostrar algunas salas para verificar
salas = {}
for o in ordenes:
    sala = o.get('x_studio_sala_de_proceso') or 'Sin Sala'
    salas[sala] = salas.get(sala, 0) + 1
print(f"\nSalas encontradas:")
for s, c in sorted(salas.items(), key=lambda x: -x[1])[:10]:
    print(f"  {s}: {c}")
