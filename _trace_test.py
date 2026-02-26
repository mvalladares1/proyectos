"""Trace PACK0021507 step by step"""
import sys
sys.path.insert(0, '.')
from shared.odoo_client import OdooClient

o = OdooClient(username='mvalladares@riofuturo.cl', password='c0766224bec30cac071ffe43a858c9ccbd521ddd')

def m2o_id(v):
    if isinstance(v, (list, tuple)) and len(v) >= 1:
        return v[0]
    if isinstance(v, int):
        return v
    return None

def m2o_name(v):
    if isinstance(v, (list, tuple)) and len(v) >= 2:
        return str(v[1])
    return None

def short(n):
    if n and n.upper().startswith("PACK"):
        r = n[4:].strip()
        return r if r else n
    return n or ""

def find_mo(pid):
    sml = o.search_read('stock.move.line', [['result_package_id', '=', pid]], ['move_id'], limit=1)
    if not sml:
        return None
    mid = m2o_id(sml[0].get('move_id'))
    if not mid:
        return None
    mv = o.search_read('stock.move', [['id', '=', mid]], ['production_id'], limit=1)
    if not mv:
        return None
    mo_id = m2o_id(mv[0].get('production_id'))
    if not mo_id:
        return None
    mos = o.search_read('mrp.production', [['id', '=', mo_id]], ['id', 'name'], limit=1)
    return mos[0] if mos else None

def get_consumidos(mo_id):
    mvs = o.search_read('stock.move', [['raw_material_production_id', '=', mo_id], ['state', '=', 'done']], ['id'])
    if not mvs:
        return []
    mids = [m['id'] for m in mvs]
    smls = o.search_read('stock.move.line', [['move_id', 'in', mids], ['package_id', '!=', False]], ['package_id'])
    seen = {}
    for s in smls:
        pid = m2o_id(s.get('package_id'))
        pname = m2o_name(s.get('package_id'))
        if pid and pid not in seen:
            seen[pid] = pname or str(pid)
    return list(seen.items())

def buscar_recepcion(pid):
    smls = o.search_read('stock.move.line', [['result_package_id', '=', pid]], ['picking_id'], limit=5)
    for s in smls:
        pick_id = m2o_id(s.get('picking_id'))
        if not pick_id:
            continue
        picks = o.search_read('stock.picking', [
            ['id', '=', pick_id],
            ['picking_type_id', 'in', [1, 217, 164]],
        ], ['name', 'x_studio_gua_de_despacho', 'partner_id', 'date_done'], limit=1)
        if picks:
            p = picks[0]
            return {
                'guia': p.get('x_studio_gua_de_despacho') or '',
                'proveedor': m2o_name(p.get('partner_id')) or ''
            }
    return None

def trace_chain(pid, pname, chain, visited, depth=0):
    """Return list of {chain: [...], guia: str, productor: str}"""
    if pid in visited or depth > 15:
        return []
    visited.add(pid)
    
    mo = find_mo(pid)
    if not mo:
        recep = buscar_recepcion(pid)
        if recep:
            return [{"chain": chain, "guia": recep["guia"], "productor": recep["proveedor"]}]
        return []  # no trazability
    
    consumidos = get_consumidos(mo["id"])
    if not consumidos:
        recep = buscar_recepcion(pid)
        if recep:
            return [{"chain": chain, "guia": recep["guia"], "productor": recep["proveedor"]}]
        return []
    
    results = []
    for cid, cname in consumidos:
        new_chain = chain + [short(cname)]
        sub = trace_chain(cid, cname, new_chain, visited, depth + 1)
        results.extend(sub)
    return results

# ========== MAIN ==========
print("=== PACK0021507 ===", flush=True)
pkg = o.search_read('stock.quant.package', [['name', '=', 'PACK0021507']], ['id', 'name'], limit=1)
print(f"Package: {pkg}", flush=True)

if not pkg:
    print("NOT FOUND")
    sys.exit(1)

pid = pkg[0]['id']
mo = find_mo(pid)
print(f"MO: {mo}", flush=True)

consumidos = get_consumidos(mo['id'])
consumidos_str = " - ".join(short(n) for _, n in consumidos)
print(f"Consumidos ({len(consumidos)}): {consumidos_str}", flush=True)
print(flush=True)

# Trace each consumed pallet
print(f"{'Pallet Origen':<16}  {'Cadena de Trazabilidad':<70}  {'Guía':<10}  {'Productor'}", flush=True)
print("-" * 140, flush=True)

total_filas = 0
for c_id, c_name in consumidos:
    visited = set()
    paths = trace_chain(c_id, c_name, [short(c_name)], visited, 0)
    if not paths:
        cadena = "NO TIENE TRAZABILIDAD"
        print(f"{short(c_name):<16}  {cadena:<70}  {'':10}  ", flush=True)
        total_filas += 1
    else:
        for p in paths:
            cadena = " → ".join(p["chain"])
            print(f"{short(c_name):<16}  {cadena:<70}  {p['guia']:<10}  {p['productor']}", flush=True)
            total_filas += 1

print(flush=True)
print(f"Total filas: {total_filas}", flush=True)
print("DONE", flush=True)
