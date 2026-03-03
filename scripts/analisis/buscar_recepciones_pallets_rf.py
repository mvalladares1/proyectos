"""
Busca recepciones asociadas a pallets específicos y verifica overrides
Los pallets sin PACK00 se normalizan agregándolo
"""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from shared.odoo_client import OdooClient

URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Lista de pallets a buscar (raw)
RAW_PALLETS = """
30548 30535 30547 30536 30537 30546 30552 30549 30540 30545 30551 30550 30539 30541 30532 30542 30534 30533 30358 30531 30529 30530 30528 30883 30880 30879
30051 30053 30055 30050 30054 30052 30049 27946 27947 30048 29281 29279 28754 29503 29250 29506 29265 29254 29255 28874 29253 28756 29229 29282 28738
28788 28760 28762 29308 28763 28772 28765 28789 28767 28764 28773 29321 29227 29217 29218 29211 29502 29504 29971 29969 29964 29967 29970 29972
PACK0023406 PACK0023412 PACK0023403 PACK0023392 PACK0023391 PACK0022653 PACK0021007 PACK0021011 PACK0021008 PACK0021735 PACK0021012 PACK0023540 PACK0021014 PACK0023539 PACK0023691 PACK0023696 PACK0023695 PACK0024134 PACK0024127 PACK0024075 PACK0024140 PACK0024139 PACK0024141 PACK0021720
28042 27932 27945 27948 27917 27930 28519 27944 27943 27914 25987 28043 28504 28505 28518 28507 27538 26365 27915 27929 27931 27928 27535 28044
27527 27496 26185 25691 27445 27544 25954 25984 26936 27540 27450 26938 25871 26227 27446 25979 25985 25947 26223 26233 25986 25979 25958 26186
25938 25949 25946 25951 25950 25956 25957 26226 27356 27448 27451 25422 25419 25417 25852 26214 26224 26228 25811 26187 26188 26191 27497 27528
26221 26219 26201 26766 26762 26763 26767 26764 26768 26765 26364 26362 26361 26360 26357 26358 26356 26355 26189 26200 26182 26194 26196 26193
26106 26101 26106 26100 26105 26099 26104 26222 26102 26220 25722 25723 26199 25973 25974 25975 25976 25793 25773 25776 25774 25994 25962 25959
PACK0024744 PACK0024743 PACK0024412 PACK0024409 PACK0024413 PACK0024407 PACK0024406 PACK0024408 PACK0024404 PACK0024491 PACK0024611 PACK0024405 PACK0024614 PACK0024615 PACK0024485 PACK0024500 PACK0024502 PACK0024501 PACK0023405 PACK0023415 PACK0024444 PACK0024451 PACK0024484 PACK0024236
PACK0023406 PACK0023412 PACK0023403 PACK0023392 PACK0023391 PACK0022653 PACK0021007 PACK0021011 PACK0021008 PACK0021735 PACK0021012 PACK0023540 PACK0021014 PACK0023539 PACK0023691 PACK0023696 PACK0023695 PACK0024134 PACK0024127 PACK0024075 PACK0024140 PACK0024139 PACK0024141 PACK0021720
22648 22651 22652 22650 21746 22286 22285 22332 22331 22330 22357 22356 22353 22348 21200 22346 22344 22649 22646 22631 22630 22633 22632 22647
PACK0021010 PACK0018697 PACK0018693 PACK0018691 PACK0018690 PACK0021203 PACK0018607 PACK0018608 PACK0018610 PACK0018609 PACK0021917 PACK0018596 PACK0018595 PACK0018593 PACK0018592 PACK0021937 PACK0021938 PACK0021934 PACK0021939 PACK0021933 PACK0021932 PACK0020102 PACK0020140 PACK0020146
PACK0021105 PACK0021070 PACK0021108 PACK0021113 PACK0021069 PACK0021068 PACK0020094 PACK0021110 PACK0021071 PACK0019999 PACK0019988 PACK0021201 PACK0021202 PACK0020424 PACK0020423 PACK0020405 PACK0020368 PACK0019448 PACK0020384 PACK0020070 PACK0020093
"""

BATCH = 200

def normalize_pallet(p):
    """Normaliza el nombre del pallet agregando PACK00 si es solo número"""
    p = p.strip()
    if not p:
        return None
    # Si es solo números, agregar PACK00
    if p.isdigit():
        return f"PACK00{p}"
    return p

def safe_m2o(val):
    if isinstance(val, list) and len(val) >= 2:
        return val[1]
    return str(val) if val else ''

def safe_m2o_id(val):
    if isinstance(val, list) and len(val) >= 2:
        return val[0]
    return val if val else None

def main():
    print("=" * 80)
    print("BÚSQUEDA DE RECEPCIONES POR PALLETS RF->VLK")
    print("=" * 80)
    
    # 1. Parsear pallets
    print("\n[1/5] Parseando lista de pallets...")
    pallets = []
    for line in RAW_PALLETS.strip().split('\n'):
        for p in line.split():
            normalized = normalize_pallet(p)
            if normalized:
                pallets.append(normalized)
    
    # Eliminar duplicados manteniendo orden
    pallets = list(dict.fromkeys(pallets))
    print(f"  Total pallets únicos: {len(pallets)}")
    print(f"  Primeros 10: {pallets[:10]}")
    
    # 2. Conectar a Odoo
    print("\n[2/5] Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD, url=URL, db=DB)
    print("  OK Conectado")
    
    # 3. Buscar los PAQUETES por nombre (stock.quant.package, NO stock.lot)
    print("\n[3/5] Buscando paquetes en stock.quant.package...")
    all_packages = []
    for i in range(0, len(pallets), BATCH):
        batch = pallets[i:i+BATCH]
        packages = odoo.search_read(
            'stock.quant.package',
            [['name', 'in', batch]],
            ['id', 'name'],
            limit=5000,
        )
        all_packages.extend(packages)
        print(f"    Batch {i//BATCH + 1}: {len(packages)} paquetes encontrados")
    
    print(f"  Total paquetes encontrados: {len(all_packages)}")
    package_ids = [p['id'] for p in all_packages]
    package_map = {p['id']: p for p in all_packages}
    package_name_map = {p['name']: p['id'] for p in all_packages}
    
    # Pallets no encontrados
    package_names_found = {p['name'] for p in all_packages}
    not_found = [p for p in pallets if p not in package_names_found]
    if not_found:
        print(f"  ADVERTENCIA: {len(not_found)} pallets no encontrados")
        print(f"    Primeros 10: {not_found[:10]}")
    
    # 4. Buscar las recepciones donde se registraron estos paquetes
    print("\n[4/5] Buscando recepciones de estos paquetes...")
    all_receptions = []
    for i in range(0, len(package_ids), BATCH):
        batch = package_ids[i:i+BATCH]
        # Buscar en stock.move.line donde result_package_id es el paquete (se creó en esa recepción)
        mlines = odoo.search_read(
            'stock.move.line',
            [
                ['result_package_id', 'in', batch],
                ['picking_id.picking_type_id.code', '=', 'incoming'],
                ['state', '=', 'done'],
            ],
            ['result_package_id', 'picking_id', 'qty_done', 'product_id', 'lot_id'],
            limit=50000,
        )
        all_receptions.extend(mlines)
        print(f"    Batch {i//BATCH + 1}: {len(mlines)} recepciones")
    
    print(f"  Total líneas de recepción: {len(all_receptions)}")
    
    # Agrupar por picking
    picking_to_packages = {}
    for ml in all_receptions:
        pick_id = safe_m2o_id(ml.get('picking_id'))
        pick_name = safe_m2o(ml.get('picking_id'))
        pkg_id = safe_m2o_id(ml.get('result_package_id'))
        pkg_name = package_map.get(pkg_id, {}).get('name', '')
        
        if pick_name not in picking_to_packages:
            picking_to_packages[pick_name] = {'id': pick_id, 'packages': []}
        if pkg_name and pkg_name not in picking_to_packages[pick_name]['packages']:
            picking_to_packages[pick_name]['packages'].append(pkg_name)
    
    print(f"  Recepciones únicas: {len(picking_to_packages)}")
    
    # 5. Cargar datos de las recepciones
    print("\n[5/5] Cargando datos de recepciones...")
    picking_ids = [v['id'] for v in picking_to_packages.values() if v['id']]
    all_picks = []
    for i in range(0, len(picking_ids), BATCH):
        batch = picking_ids[i:i+BATCH]
        picks = odoo.search_read(
            'stock.picking',
            [['id', 'in', batch]],
            ['id', 'name', 'origin', 'partner_id', 'date_done', 'picking_type_id',
             'x_studio_acopio', 'x_studio_categora_de_producto'],
            limit=5000,
        )
        all_picks.extend(picks)
    
    pick_data = {p['name']: p for p in all_picks}
    
    # Clasificar por prefijo
    rfp_picks = []  # RF/RFP/IN - originalmente RF
    vlk_picks = []  # RF/Vilk/IN - originalmente VLK
    other_picks = []
    
    for pick_name, info in picking_to_packages.items():
        data = pick_data.get(pick_name, {})
        entry = {
            'picking': pick_name,
            'origin': data.get('origin', ''),
            'partner': safe_m2o(data.get('partner_id', '')),
            'date_done': str(data.get('date_done', ''))[:10],
            'acopio': data.get('x_studio_acopio', ''),
            'categoria': data.get('x_studio_categora_de_producto', ''),
            'pallets': info['packages'],
            'num_pallets': len(info['packages']),
        }
        
        if pick_name.startswith('RF/RFP/IN'):
            rfp_picks.append(entry)
        elif pick_name.startswith('RF/Vilk/') or 'VLK' in pick_name.upper():
            vlk_picks.append(entry)
        else:
            other_picks.append(entry)
    
    # Mostrar resultados
    print("\n" + "=" * 80)
    print("RESULTADOS")
    print("=" * 80)
    
    print(f"\n== RECEPCIONES RF/RFP/IN (originalmente RF): {len(rfp_picks)} ==")
    print("   (Estas NO deben estar en overwrite a VILKUN)")
    for p in sorted(rfp_picks, key=lambda x: x['picking']):
        print(f"   {p['picking']} | {p['date_done']} | {p['partner'][:30]:30} | {p['num_pallets']} pallets")
    
    print(f"\n== RECEPCIONES RF/Vilk/IN (originalmente VLK): {len(vlk_picks)} ==")
    for p in sorted(vlk_picks, key=lambda x: x['picking']):
        print(f"   {p['picking']} | {p['date_done']} | {p['partner'][:30]:30} | {p['num_pallets']} pallets")
    
    if other_picks:
        print(f"\n== OTRAS RECEPCIONES: {len(other_picks)} ==")
        for p in sorted(other_picks, key=lambda x: x['picking']):
            print(f"   {p['picking']} | {p['date_done']} | {p['partner'][:30]:30} | {p['num_pallets']} pallets")
    
    # Generar lista de pickings RF/RFP a remover del overwrite
    rfp_picking_names = [p['picking'] for p in rfp_picks]
    
    print("\n" + "=" * 80)
    print("PICKINGS A REMOVER DEL OVERWRITE (son RF reales):")
    print("=" * 80)
    for p in sorted(rfp_picking_names):
        print(f"   {p}")
    
    # Guardar para uso posterior
    output_path = os.path.join(os.path.dirname(__file__), '..', '..', 'output', 'pallets_rf_to_remove_override.txt')
    with open(output_path, 'w') as f:
        f.write('\n'.join(sorted(rfp_picking_names)))
    print(f"\nGuardado en: {output_path}")
    
    return rfp_picking_names


if __name__ == '__main__':
    main()
