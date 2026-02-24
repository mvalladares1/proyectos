"""
Review Forense: Recepciones Específicas - Trazabilidad de Pallets
=================================================================
Para una lista de recepciones (stock.picking), genera un Excel con:
- Hoja 1: Info general de cada recepción (guía, fecha, creador, productor, acopio, etc.)
- Hoja 2: Pallets (lotes) de esas recepciones, indicando si fueron consumidos
           en una fabricación (y cuál), o su ubicación actual si no.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
from shared.odoo_client import OdooClient

# --- Credenciales ---
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
EXCEL_PATH = os.path.join(OUTPUT_DIR, f"forense_recepciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

BATCH = 200

# --- Lista de recepciones ---
RECEPCIONES_RAW = """
RF/RFP/IN/01151
RF/RFP/IN/01156
RF/RFP/IN/01181
RF/RFP/IN/01192
RF/RFP/IN/00386
RF/RFP/IN/00684
RF/RFP/IN/01228
RF/RFP/IN/01191
RF/RFP/IN/01193
RF/RFP/IN/00390
RF/RFP/IN/00563
RF/RFP/IN/00588
RF/RFP/IN/00245
RF/RFP/IN/01245
RF/RFP/IN/00988
RF/RFP/IN/01061
RF/RFP/IN/00655
RF/RFP/IN/00214
RF/RFP/IN/00395
RF/RFP/IN/00471
RF/RFP/IN/00498
RF/RFP/IN/01049
RF/RFP/IN/00115
RF/RFP/IN/00116
RF/RFP/IN/00119
RF/RFP/IN/00430
RF/RFP/IN/00499
RF/RFP/IN/00352
RF/RFP/IN/00740
RF/RFP/IN/00286
RF/RFP/IN/00329
RF/RFP/IN/01044
RF/RFP/IN/01254
RF/RFP/IN/01246
RF/RFP/IN/01327
RF/RFP/IN/01347
RF/RFP/IN/01348
RF/RFP/IN/01349
RF/RFP/IN/01383
RF/RFP/IN/01271
RF/RFP/IN/01288
RF/RFP/IN/00664
RF/RFP/IN/01050
RF/RFP/IN/01159
RF/RFP/IN/01511
RF/RFP/IN/01456
RF/RFP/IN/01287
RF/RFP/IN/01446
RF/RFP/IN/01244
RF/RFP/IN/01392
RF/RFP/IN/01455
RF/RFP/IN/01596
RF/RFP/IN/01393
RF/RFP/IN/01517
RF/RFP/IN/01554
RF/RFP/IN/01653
RF/RFP/IN/01447
RF/RFP/IN/01448
RF/RFP/IN/01684
RF/RFP/IN/01621
RF/RFP/IN/00085
RF/RFP/IN/01681
RF/RFP/IN/01682
RF/RFP/IN/01683
RF/RFP/IN/01665
RF/RFP/IN/01491
RF/RFP/IN/01635
RF/RFP/IN/01687
RF/RFP/IN/01620
RF/RFP/IN/01565
RF/RFP/IN/01623
RF/RFP/IN/01778
RF/RFP/IN/00140
RF/RFP/IN/00160
RF/RFP/IN/00161
RF/RFP/IN/00162
RF/RFP/IN/00277
RF/RFP/IN/01680
RF/RFP/IN/01797
RF/RFP/IN/01516
RF/RFP/IN/01562
RF/RFP/IN/01638
RF/RFP/IN/01593
RF/RFP/IN/01597
RF/RFP/IN/01657
RF/RFP/IN/01669
RF/RFP/IN/01658
RF/RFP/IN/01622
RF/RFP/IN/01927
RF/RFP/IN/01759
RF/RFP/IN/01765
RF/RFP/IN/01807
RF/RFP/IN/01834
RF/RFP/IN/01809
RF/RFP/IN/01830
RF/RFP/IN/01564
RF/RFP/IN/01920
RF/RFP/IN/01996
RF/RFP/IN/01760
RF/RFP/IN/01957
RF/RFP/IN/01959
RF/RFP/IN/01781
RF/RFP/IN/01924
RF/RFP/IN/01968
RF/RFP/IN/01991
RF/RFP/IN/01976
RF/RFP/IN/01981
RF/RFP/IN/02038
RF/RFP/IN/02042
RF/RFP/IN/02065
RF/RFP/IN/02076
RF/RFP/IN/02001
RF/RFP/IN/02003
RF/RFP/IN/02069
RF/RFP/IN/02089
RF/RFP/IN/02075
RF/RFP/IN/02093
RF/RFP/IN/02078
RF/RFP/IN/02056
RF/RFP/IN/02059
RF/RFP/IN/02024
RF/RFP/IN/02077
RF/RFP/IN/01647
RF/RFP/IN/00028
RF/RFP/IN/00114
RF/RFP/IN/00118
RF/RFP/IN/00082
RF/RFP/IN/00284
RF/RFP/IN/01804
RF/RFP/IN/00451
RF/RFP/IN/01852
RF/RFP/IN/02244
RF/RFP/IN/02247
RF/RFP/IN/02258
RF/RFP/IN/02271
RF/RFP/IN/02256
RF/RFP/IN/02201
RF/RFP/IN/02227
RF/RFP/IN/02254
RF/RFP/IN/02223
RF/RFP/IN/02270
RF/RFP/IN/02229
RF/RFP/IN/02255
RF/RFP/IN/02171
RF/RFP/IN/02228
RF/RFP/IN/02248
RF/RFP/IN/02251
RF/RFP/IN/02272
RF/RFP/IN/02273
RF/RFP/IN/02263
RF/RFP/IN/02288
RF/RFP/IN/02289
RF/RFP/IN/01925
RF/RFP/IN/01936
RF/RFP/IN/01994
RF/RFP/IN/02136
RF/RFP/IN/02297
RF/RFP/IN/01395
RF/RFP/IN/01461
RF/RFP/IN/01805
RF/RFP/IN/02261
RF/RFP/IN/02092
RF/RFP/IN/02131
RF/RFP/IN/02108
RF/RFP/IN/02127
RF/RFP/IN/02106
RF/RFP/IN/02135
RF/RFP/IN/02177
RF/RFP/IN/02126
RF/RFP/IN/02167
RF/RFP/IN/02170
RF/RFP/IN/02182
RF/RFP/IN/02212
RF/RFP/IN/02262
RF/RFP/IN/02243
RF/RFP/IN/02290
RF/RFP/IN/02249
RF/RFP/IN/02471
RF/RFP/IN/02103
RF/RFP/IN/00177
RF/RFP/IN/00178
RF/RFP/IN/00180
RF/RFP/IN/00181
RF/RFP/IN/00182
RF/RFP/IN/00183
RF/RFP/IN/00184
RF/RFP/IN/00185
RF/RFP/IN/00190
RF/RFP/IN/00467
RF/RFP/IN/00638
RF/RFP/IN/00267
RF/RFP/IN/00153
RF/RFP/IN/00154
RF/RFP/IN/00155
RF/RFP/IN/00156
RF/RFP/IN/00157
RF/RFP/IN/00158
RF/RFP/IN/00159
RF/RFP/IN/00163
RF/RFP/IN/00164
RF/RFP/IN/00165
RF/RFP/IN/00166
RF/RFP/IN/00167
RF/RFP/IN/00168
RF/RFP/IN/00169
RF/RFP/IN/00170
RF/RFP/IN/00171
RF/RFP/IN/00172
RF/RFP/IN/00173
RF/RFP/IN/00174
RF/RFP/IN/00175
RF/RFP/IN/00176
RF/RFP/IN/01117
RF/RFP/IN/01155
"""

RECEPCIONES = [r.strip() for r in RECEPCIONES_RAW.strip().split('\n') if r.strip()]


def safe_m2o(val):
    if isinstance(val, list) and len(val) >= 2:
        return val[1]
    return str(val) if val else ''


def parse_date_parts(date_val):
    """Extrae mes y dia de un campo de fecha Odoo (string o False)."""
    if not date_val or date_val == False:
        return '', ''
    date_str = str(date_val)[:10]  # 'YYYY-MM-DD'
    try:
        parts = date_str.split('-')
        return int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        return '', ''


def main():
    print("=" * 80)
    print("REVIEW FORENSE: RECEPCIONES ESPECÍFICAS")
    print(f"  {len(RECEPCIONES)} recepciones a analizar")
    print("=" * 80)

    # ── 1. Conectar ──────────────────────────────────────────────────────────
    print("\n[1/6] Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD, url=URL, db=DB)
    print("  ✓ Conectado\n")

    # ── 2. Buscar recepciones por nombre ─────────────────────────────────────
    # Los nombres en Odoo tienen prefijo "WH/" -> "WH/RFP/IN24//00XXX" o similar
    # Probar búsqueda flexible con ilike
    print("[2/6] Buscando recepciones en Odoo...")

    all_pickings = []
    not_found = []

    for i in range(0, len(RECEPCIONES), BATCH):
        batch_names = RECEPCIONES[i:i + BATCH]
        # Buscar con ilike para cada nombre (parte numérica)
        domain = ['|'] * (len(batch_names) - 1)
        for name in batch_names:
            # Extraer solo la parte final del nombre para búsqueda flexible
            domain.append(['name', 'ilike', name])

        picks = odoo.search_read(
            'stock.picking',
            domain,
            [
                'id', 'name', 'origin', 'state', 'date_done',
                'scheduled_date', 'create_date', 'create_uid',
                'partner_id', 'picking_type_id',
                'x_studio_gua_de_despacho',
                'x_studio_precio_kg',
                'x_studio_kg_netos',
                'x_studio_kg_brutos',
                'x_studio_kg_brutos_1',
                'x_studio_kg_hechos',
                'x_studio_acopio',
                'x_studio_categora_de_producto',
                'x_studio_fecha_de_emisin_gdd',
                'x_studio_fecha_de_ingreso',
                'x_studio_calidad',
                'x_studio_nombre_conductor',
                'x_studio_patente_camion',
            ],
            limit=5000,
        )
        all_pickings.extend(picks)
        print(f"    Batch {i // BATCH + 1}: {len(picks)} encontradas")

    # Deduplicar por ID
    pick_by_id = {p['id']: p for p in all_pickings}
    all_pickings = list(pick_by_id.values())

    # Mapear por nombre para verificar cuáles se encontraron
    pick_by_name = {}
    for p in all_pickings:
        pick_by_name[p['name']] = p
        # También mapear sin prefijo WH/
        short = p['name'].replace('WH/', '').replace('24//', '/').replace('25//', '/')
        pick_by_name[short] = p

    for rname in RECEPCIONES:
        found = False
        for pname, pdata in pick_by_name.items():
            # Comparar la parte numérica final
            if rname.split('/')[-1] in pname:
                found = True
                break
        if not found:
            not_found.append(rname)

    print(f"\n  ✓ {len(all_pickings)} recepciones encontradas en Odoo")
    if not_found:
        print(f"  ⚠ {len(not_found)} no encontradas: {not_found[:5]}...")

    picking_ids = [p['id'] for p in all_pickings]

    # ── 3. Obtener move.lines (pallets/lotes) de las recepciones ─────────────
    print(f"\n[3/6] Obteniendo pallets (stock.move.line) de las recepciones...")

    all_move_lines = []
    for i in range(0, len(picking_ids), BATCH):
        batch = picking_ids[i:i + BATCH]
        mlines = odoo.search_read(
            'stock.move.line',
            [['picking_id', 'in', batch]],
            [
                'id', 'move_id', 'product_id', 'lot_id', 'lot_name',
                'qty_done', 'picking_id', 'date', 'reference',
                'location_id', 'location_dest_id',
                'x_studio_precio_unitario', 'x_studio_coste',
            ],
            limit=10000,
        )
        all_move_lines.extend(mlines)
        print(f"    Batch {i // BATCH + 1}: {len(mlines)} líneas")

    print(f"  ✓ Total: {len(all_move_lines)} líneas de stock (pallets)")

    # Recolectar lot IDs
    lot_ids = set()
    for ml in all_move_lines:
        if ml.get('lot_id') and ml['lot_id']:
            lid = ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id']
            lot_ids.add(lid)

    print(f"  Lotes únicos: {len(lot_ids)}")

    # ── 4. Buscar consumos en fabricaciones para estos lotes ─────────────────
    print(f"\n[4/6] Buscando consumos en fabricaciones para {len(lot_ids)} lotes...")

    # Buscar stock.move.line donde lot_id está en nuestros lotes
    # y el movimiento es de consumo en fabricación (raw_material_production_id)
    lot_consumption = {}  # lot_id -> {'fab_name': ..., 'fab_id': ..., 'qty': ..., ...}

    lots_list = list(lot_ids)
    for i in range(0, len(lots_list), BATCH):
        batch = lots_list[i:i + BATCH]
        # Buscar move.lines donde se consumieron estos lotes
        consumption_mlines = odoo.search_read(
            'stock.move.line',
            [
                ['lot_id', 'in', batch],
                ['move_id.raw_material_production_id', '!=', False],
                ['state', '=', 'done'],
            ],
            [
                'lot_id', 'move_id', 'qty_done', 'date',
                'location_id', 'location_dest_id',
            ],
            limit=10000,
        )
        print(f"    Batch {i // BATCH + 1}: {len(consumption_mlines)} consumos encontrados")

        for cml in consumption_mlines:
            lid = cml['lot_id'][0] if isinstance(cml['lot_id'], list) else cml['lot_id']
            if lid not in lot_consumption:
                lot_consumption[lid] = []
            lot_consumption[lid].append(cml)

    print(f"  ✓ {len(lot_consumption)} lotes con consumo en fabricación")

    # Obtener los move_ids de consumo para sacar la fabricación asociada
    consumption_move_ids = set()
    for entries in lot_consumption.values():
        for e in entries:
            mid = e['move_id'][0] if isinstance(e['move_id'], list) else e['move_id']
            consumption_move_ids.add(mid)

    # Leer los stock.move para obtener raw_material_production_id
    move_to_fab = {}  # move_id -> production_id
    if consumption_move_ids:
        cmids = list(consumption_move_ids)
        for i in range(0, len(cmids), BATCH):
            batch = cmids[i:i + BATCH]
            cmoves = odoo.search_read(
                'stock.move',
                [['id', 'in', batch]],
                ['id', 'raw_material_production_id'],
            )
            for cm in cmoves:
                if cm.get('raw_material_production_id'):
                    fab_id = cm['raw_material_production_id'][0] if isinstance(cm['raw_material_production_id'], list) else cm['raw_material_production_id']
                    move_to_fab[cm['id']] = fab_id

    # Leer las fabricaciones
    fab_ids = set(move_to_fab.values())
    fab_map = {}
    if fab_ids:
        fids = list(fab_ids)
        for i in range(0, len(fids), BATCH):
            batch = fids[i:i + BATCH]
            fabs = odoo.search_read(
                'mrp.production',
                [['id', 'in', batch]],
                ['id', 'name', 'state', 'product_id', 'date_start',
                 'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso'],
            )
            for f in fabs:
                fab_map[f['id']] = f

    print(f"  ✓ {len(fab_map)} fabricaciones asociadas cargadas")

    # ── 5. Obtener ubicación actual de lotes no consumidos ───────────────────
    print(f"\n[5/6] Obteniendo ubicación actual de lotes...")

    # Para lotes que NO fueron consumidos, buscar su quant actual
    unconsumed_lots = lot_ids - set(lot_consumption.keys())
    print(f"  Lotes consumidos: {len(lot_consumption)}")
    print(f"  Lotes sin consumo detectado: {len(unconsumed_lots)}")

    lot_location = {}  # lot_id -> location info
    if unconsumed_lots:
        ulots = list(unconsumed_lots)
        for i in range(0, len(ulots), BATCH):
            batch = ulots[i:i + BATCH]
            quants = odoo.search_read(
                'stock.quant',
                [['lot_id', 'in', batch], ['quantity', '>', 0]],
                ['lot_id', 'product_id', 'quantity', 'location_id'],
            )
            for q in quants:
                lid = q['lot_id'][0] if isinstance(q['lot_id'], list) else q['lot_id']
                lot_location[lid] = {
                    'ubicacion': safe_m2o(q.get('location_id', '')),
                    'qty_disponible': q.get('quantity', 0),
                }

    # También buscar consumo para los "unconsumed" por si fueron movidos
    # pero no a fabricación
    if unconsumed_lots:
        ulots = list(unconsumed_lots)
        for i in range(0, len(ulots), BATCH):
            batch = ulots[i:i + BATCH]
            quants_all = odoo.search_read(
                'stock.quant',
                [['lot_id', 'in', batch]],
                ['lot_id', 'quantity', 'location_id'],
            )
            for q in quants_all:
                lid = q['lot_id'][0] if isinstance(q['lot_id'], list) else q['lot_id']
                if lid not in lot_location:
                    lot_location[lid] = {
                        'ubicacion': safe_m2o(q.get('location_id', '')),
                        'qty_disponible': q.get('quantity', 0),
                    }

    print(f"  ✓ {len(lot_location)} lotes con ubicación actual")

    # ── 6. Obtener datos de OC (purchase.order) ──────────────────────────────
    print(f"\n[6/7] Obteniendo datos de Ordenes de Compra...")

    # Recolectar origins únicos de los pickings
    oc_origins = set()
    for p in all_pickings:
        origin = p.get('origin', '')
        if origin:
            oc_origins.add(origin)

    oc_map = {}  # origin_name -> {name, create_uid, partner_id, ...}
    if oc_origins:
        origins_list = list(oc_origins)
        for i in range(0, len(origins_list), BATCH):
            batch = origins_list[i:i + BATCH]
            domain = ['|'] * (len(batch) - 1)
            for o in batch:
                domain.append(['name', '=', o])
            ocs = odoo.search_read(
                'purchase.order',
                domain,
                ['id', 'name', 'create_uid', 'partner_id', 'date_order', 'state'],
                limit=5000,
            )
            for oc in ocs:
                oc_map[oc['name']] = oc

    print(f"  ✓ {len(oc_map)} ordenes de compra cargadas")

    # ── 7. Construir Excel ───────────────────────────────────────────────────
    print(f"\n[7/7] Construyendo Excel...")
    import pandas as pd

    # === HOJA 1: Recepciones ===
    rec_rows = []
    for p in all_pickings:
        # Usar date_done o fecha_de_ingreso como fecha principal
        fecha_ref = p.get('date_done', '') or p.get('x_studio_fecha_de_ingreso', '') or p.get('scheduled_date', '')
        mes, dia = parse_date_parts(fecha_ref)

        # OC info
        origin = p.get('origin', '') or ''
        oc = oc_map.get(origin, {})
        creador_oc = safe_m2o(oc.get('create_uid', '')) if oc else ''

        # Kg: usar kg_hechos como fallback si netos/brutos están en 0
        kg_netos = p.get('x_studio_kg_netos', 0) or 0
        kg_brutos = p.get('x_studio_kg_brutos', 0) or p.get('x_studio_kg_brutos_1', 0) or 0
        kg_hechos = p.get('x_studio_kg_hechos', 0) or 0

        rec_rows.append({
            'Albaran': p.get('name', ''),
            'Estado': p.get('state', ''),
            'OC': origin,
            'Creador OC': creador_oc,
            'Productor': safe_m2o(p.get('partner_id', '')),
            'Guia Despacho': p.get('x_studio_gua_de_despacho', '') or '',
            'Fecha Emision GDD': p.get('x_studio_fecha_de_emisin_gdd', '') or '',
            'Fecha Ingreso': p.get('x_studio_fecha_de_ingreso', '') or '',
            'Fecha Realizacion': p.get('date_done', '') or '',
            'Fecha Programada': p.get('scheduled_date', '') or '',
            'Mes': mes,
            'Dia': dia,
            'Creador Recepcion': safe_m2o(p.get('create_uid', '')),
            'Fecha Creacion': p.get('create_date', '') or '',
            'Acopio': p.get('x_studio_acopio', '') or '',
            'Categoria Producto': p.get('x_studio_categora_de_producto', '') or '',
            'Precio Kg': p.get('x_studio_precio_kg', 0) or 0,
            'Kg Netos': kg_netos,
            'Kg Brutos': kg_brutos,
            'Kg Hechos': kg_hechos,
            'Calidad': p.get('x_studio_calidad', '') or '',
            'Conductor': p.get('x_studio_nombre_conductor', '') or '',
            'Patente Camion': p.get('x_studio_patente_camion', '') or '',
            'Tipo Operacion': safe_m2o(p.get('picking_type_id', '')),
        })

    df_recepciones = pd.DataFrame(rec_rows)
    if not df_recepciones.empty:
        df_recepciones.sort_values('Albaran', inplace=True)

    # === HOJA 2: Pallets / Lotes ===
    pallet_rows = []
    pick_map = {p['id']: p for p in all_pickings}

    for ml in all_move_lines:
        pick_id = ml['picking_id'][0] if isinstance(ml['picking_id'], list) else ml['picking_id']
        pick = pick_map.get(pick_id, {})

        lot_id_val = None
        lot_name = ''
        if ml.get('lot_id') and ml['lot_id']:
            lot_id_val = ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id']
            lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else ''
        elif ml.get('lot_name'):
            lot_name = ml['lot_name']

        # Determinar estado de consumo
        consumido = False
        fab_name = ''
        fab_producto = ''
        fab_estado = ''
        fab_fecha = ''
        qty_consumida = 0

        if lot_id_val and lot_id_val in lot_consumption:
            consumido = True
            consumptions = lot_consumption[lot_id_val]
            # Puede haber múltiples consumos, tomar el primero
            for c in consumptions:
                mid = c['move_id'][0] if isinstance(c['move_id'], list) else c['move_id']
                fid = move_to_fab.get(mid)
                f = fab_map.get(fid, {})
                if f:
                    fab_name = f.get('name', '')
                    fab_producto = safe_m2o(f.get('product_id', ''))
                    fab_estado = f.get('state', '')
                    fab_fecha = f.get('x_studio_inicio_de_proceso', '') or f.get('date_start', '')
                    qty_consumida += c.get('qty_done', 0) or 0

        # Ubicación actual (para no consumidos)
        ubicacion_actual = ''
        qty_disponible = 0
        if lot_id_val and lot_id_val in lot_location:
            loc_info = lot_location[lot_id_val]
            ubicacion_actual = loc_info.get('ubicacion', '')
            qty_disponible = loc_info.get('qty_disponible', 0)

        # Si fue consumido, buscar también si tiene stock restante
        if consumido and lot_id_val and lot_id_val not in lot_location:
            # No tiene quant, todo fue consumido
            ubicacion_actual = 'Consumido en fabricación'

        # Determinar estado claro del pallet
        if consumido:
            estado_pallet = 'CONSUMIDO'
        elif lot_id_val and lot_id_val in lot_location:
            estado_pallet = 'DISPONIBLE'
        elif lot_name:
            estado_pallet = 'SIN STOCK'
        else:
            estado_pallet = 'SIN LOTE'

        fecha_rec = ml.get('date', '') or ''
        mes_rec, dia_rec = parse_date_parts(fecha_rec)
        mes_fab, dia_fab = parse_date_parts(fab_fecha) if consumido else ('', '')

        # OC info del picking
        pick_origin = pick.get('origin', '') or ''
        pick_oc = oc_map.get(pick_origin, {})
        pick_creador_oc = safe_m2o(pick_oc.get('create_uid', '')) if pick_oc else ''

        row = {
            'Albaran Recepcion': pick.get('name', ''),
            'OC': pick_origin,
            'Creador OC': pick_creador_oc,
            'Productor': safe_m2o(pick.get('partner_id', '')),
            'Guia Despacho': pick.get('x_studio_gua_de_despacho', '') or '',
            'Producto': safe_m2o(ml.get('product_id', '')),
            'Nombre Pallet': lot_name,
            'Estado Pallet': estado_pallet,
            'Kg Recibidos': ml.get('qty_done', 0) or 0,
            'Precio Unit.': ml.get('x_studio_precio_unitario', 0) or 0,
            'Costo': ml.get('x_studio_coste', 0) or 0,
            'Fecha Recepcion': fecha_rec,
            'Mes Recepcion': mes_rec,
            'Dia Recepcion': dia_rec,
            'Consumido En Fabricacion': fab_name if consumido else '',
            'Producto Fabricado': fab_producto if consumido else '',
            'Estado Fabricacion': fab_estado if consumido else '',
            'Fecha Fabricacion': fab_fecha if consumido else '',
            'Mes Fabricacion': mes_fab,
            'Dia Fabricacion': dia_fab,
            'Kg Consumidos': qty_consumida if consumido else 0,
            'Ubicacion Actual': ubicacion_actual if not consumido else 'Consumido en fabricacion',
            'Qty Disponible Actual': qty_disponible if not consumido else 0,
        }
        pallet_rows.append(row)

    # Si un lote fue consumido en MÚLTIPLES fabricaciones, expandir
    # (ya cubierto arriba tomando el primero, pero agreguemos todas)
    # Para simplificar, si hay múltiples consumos para un lote, agregar filas extra
    extra_rows = []
    for ml in all_move_lines:
        lot_id_val = None
        if ml.get('lot_id') and ml['lot_id']:
            lot_id_val = ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id']

        if lot_id_val and lot_id_val in lot_consumption:
            consumptions = lot_consumption[lot_id_val]
            if len(consumptions) > 1:
                pick_id = ml['picking_id'][0] if isinstance(ml['picking_id'], list) else ml['picking_id']
                pick = pick_map.get(pick_id, {})
                lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else ''

                for c in consumptions[1:]:  # Skip first (already in main rows)
                    mid = c['move_id'][0] if isinstance(c['move_id'], list) else c['move_id']
                    fid = move_to_fab.get(mid)
                    f = fab_map.get(fid, {})
                    extra_rows.append({
                        'Albaran Recepcion': pick.get('name', ''),
                        'Productor': safe_m2o(pick.get('partner_id', '')),
                        'Guia Despacho': pick.get('x_studio_gua_de_despacho', '') or '',
                        'Producto': safe_m2o(ml.get('product_id', '')),
                        'Nombre Pallet': lot_name,
                        'Estado Pallet': 'CONSUMIDO (adicional)',
                        'Kg Recibidos': 0,
                        'Precio Unit.': 0,
                        'Costo': 0,
                        'Fecha Recepcion': '',
                        'Consumido En Fabricacion': f.get('name', ''),
                        'Producto Fabricado': safe_m2o(f.get('product_id', '')),
                        'Estado Fabricacion': f.get('state', ''),
                        'Fecha Fabricacion': f.get('x_studio_inicio_de_proceso', '') or f.get('date_start', ''),
                        'Kg Consumidos': c.get('qty_done', 0) or 0,
                        'Ubicacion Actual': 'Consumido en fabricacion',
                        'Qty Disponible Actual': 0,
                    })

    pallet_rows.extend(extra_rows)

    df_pallets = pd.DataFrame(pallet_rows)
    if not df_pallets.empty:
        df_pallets.sort_values(['Albaran Recepcion', 'Nombre Pallet'], inplace=True)

    # Escribir Excel
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        df_recepciones.to_excel(writer, sheet_name='Recepciones', index=False)
        df_pallets.to_excel(writer, sheet_name='Pallets y Trazabilidad', index=False)

        # Resumen
        total_kg_rec = df_recepciones['Kg Netos'].sum() if 'Kg Netos' in df_recepciones.columns else 0
        total_kg_pall = df_pallets['Kg Recibidos'].sum() if 'Kg Recibidos' in df_pallets.columns else 0
        consumidos = len(df_pallets[df_pallets['Estado Pallet'].str.startswith('CONSUMIDO')]) if not df_pallets.empty else 0
        no_consumidos = len(df_pallets[df_pallets['Estado Pallet'] == 'DISPONIBLE']) if not df_pallets.empty else 0

        resumen = pd.DataFrame({
            'Métrica': [
                'Total Recepciones',
                'Total Pallets/Lotes',
                'Pallets Consumidos',
                'Pallets No Consumidos',
                'Total Kg Netos (Recepciones)',
                'Total Kg Recibidos (Pallets)',
                'Fabricaciones Involucradas',
                'Fecha Reporte',
            ],
            'Valor': [
                len(all_pickings),
                len(all_move_lines),
                consumidos,
                no_consumidos,
                f"{total_kg_rec:,.2f}",
                f"{total_kg_pall:,.2f}",
                len(fab_map),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ],
        })
        resumen.to_excel(writer, sheet_name='Resumen', index=False)

    print(f"\n{'=' * 80}")
    print(f"✓ EXCEL GENERADO: {EXCEL_PATH}")
    print(f"  → Hojas: 'Recepciones', 'Pallets y Trazabilidad', 'Resumen'")
    print(f"  → {len(all_pickings)} recepciones")
    print(f"  → {len(all_move_lines)} pallets/lotes")
    print(f"  → {len(lot_consumption)} lotes consumidos en fabricación")
    print(f"  → {len(fab_map)} fabricaciones involucradas")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
