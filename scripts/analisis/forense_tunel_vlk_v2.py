"""
Review Forense V2: Túnel Estático VLK — Fabricaciones + Recepciones
====================================================================
Genera Excel con:
  Hoja 1: Fabricaciones del producto "[1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK"
          desde 2025-11-01, con cada pallet consumido, su recepción, OC, productor, kg, etc.
  Hoja 2: Recepciones únicas vinculadas a esos pallets, con TODOS los campos relevantes.
  Hoja 3: Resumen.
"""

import sys, os
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
EXCEL_PATH = os.path.join(OUTPUT_DIR, f"forense_tunel_vlk_v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

BATCH = 200
FECHA_DESDE = '2025-11-01'
PRODUCTO_BUSCAR = 'TÚNEL ESTÁTICO VLK'


def safe_m2o(val):
    if isinstance(val, list) and len(val) >= 2:
        return val[1]
    return str(val) if val else ''


def safe_m2o_id(val):
    if isinstance(val, list) and len(val) >= 2:
        return val[0]
    return val if val else None


def parse_date_parts(date_val):
    """Extrae mes y dia de un campo de fecha Odoo (string o False)."""
    if not date_val or date_val == False:
        return '', ''
    date_str = str(date_val)[:10]
    try:
        parts = date_str.split('-')
        return int(parts[1]), int(parts[2])
    except (IndexError, ValueError):
        return '', ''


def main():
    print("=" * 80)
    print("REVIEW FORENSE V2: TÚNEL ESTÁTICO VLK")
    print(f"  Fecha desde: {FECHA_DESDE} hasta hoy")
    print("=" * 80)

    # ── 1. Conectar ──────────────────────────────────────────────────────────
    print("\n[1/8] Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD, url=URL, db=DB)
    print("  OK Conectado\n")

    # ── 2. Buscar producto ───────────────────────────────────────────────────
    print("[2/8] Buscando producto...")
    products = odoo.search_read(
        'product.product',
        [['name', 'ilike', PRODUCTO_BUSCAR]],
        ['id', 'name', 'default_code'],
    )
    if not products:
        print("  ERROR: Producto no encontrado!")
        return

    product_ids = [p['id'] for p in products]
    product_names = [p['name'] for p in products]
    print(f"  OK Productos: {product_names}")

    # ── 3. Buscar fabricaciones ──────────────────────────────────────────────
    print("\n[3/8] Buscando fabricaciones...")
    fabs = odoo.search_read(
        'mrp.production',
        [
            ['product_id', 'in', product_ids],
            ['create_date', '>=', FECHA_DESDE],
        ],
        [
            'id', 'name', 'state', 'product_id', 'product_qty',
            'qty_producing', 'date_start', 'date_finished',
            'create_uid', 'create_date', 'origin',
            'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
            'x_studio_sala_de_proceso', 'x_studio_dotacin',
            'x_studio_horas_de_detencin', 'x_studio_hh',
            'x_studio_hh_efectiva', 'x_studio_kghh_efectiva',
            'x_studio_kghora_efectiva',
            'x_studio_po_cliente_1', 'x_studio_nmero_de_po_1',
            'x_studio_po_asociada',
            'x_studio_cantidad_consumida', 'x_studio_consumo_mp',
            'x_studio_estado_de_odf', 'x_studio_tipo_operacion',
            'x_studio_merma_bolsas',
        ],
        limit=5000,
    )
    print(f"  OK {len(fabs)} fabricaciones encontradas")

    fab_ids = [f['id'] for f in fabs]
    fab_map = {f['id']: f for f in fabs}

    # ── 4. Obtener movimientos de consumo (stock.move) de las fabricaciones ──
    print("\n[4/8] Obteniendo movimientos de consumo (stock.move)...")
    all_moves = []
    for i in range(0, len(fab_ids), BATCH):
        batch = fab_ids[i:i + BATCH]
        moves = odoo.search_read(
            'stock.move',
            [['raw_material_production_id', 'in', batch], ['state', '=', 'done']],
            [
                'id', 'product_id', 'product_uom_qty', 'quantity_done',
                'raw_material_production_id', 'picking_id', 'reference',
                'date', 'name',
            ],
            limit=50000,
        )
        all_moves.extend(moves)
        print(f"    Batch {i // BATCH + 1}: {len(moves)} movimientos")

    print(f"  OK Total: {len(all_moves)} movimientos de consumo")
    move_ids = [m['id'] for m in all_moves]

    # ── 5. Obtener stock.move.line para saber los lotes/pallets ──────────────
    print("\n[5/8] Obteniendo líneas de detalle (stock.move.line) para lotes...")
    all_mlines = []
    for i in range(0, len(move_ids), BATCH):
        batch = move_ids[i:i + BATCH]
        mlines = odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', batch], ['state', '=', 'done']],
            [
                'id', 'move_id', 'product_id', 'lot_id', 'lot_name',
                'qty_done', 'picking_id', 'date', 'reference',
                'location_id', 'location_dest_id',
                'x_studio_precio_unitario', 'x_studio_coste',
            ],
            limit=50000,
        )
        all_mlines.extend(mlines)
        print(f"    Batch {i // BATCH + 1}: {len(mlines)} lineas")

    print(f"  OK Total: {len(all_mlines)} lineas de detalle")

    # Mapear move_id -> fabrication_id
    move_to_fab = {}
    move_map = {}
    for m in all_moves:
        move_map[m['id']] = m
        fab_id = safe_m2o_id(m.get('raw_material_production_id'))
        if fab_id:
            move_to_fab[m['id']] = fab_id

    # ── 6. Trazar lotes/pallets a su recepción original ──────────────────────
    print("\n[6/8] Trazando pallets a sus recepciones originales...")

    # Recolectar lot_ids unicos
    lot_ids = set()
    lot_name_map = {}  # lot_id -> lot_name
    for ml in all_mlines:
        if ml.get('lot_id') and ml['lot_id']:
            lid = ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id']
            lot_ids.add(lid)
            lot_name_map[lid] = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else ''

    print(f"  Lotes unicos consumidos: {len(lot_ids)}")

    # Buscar las recepciones donde se registraron estos lotes (stock.move.line de recepciones)
    lot_to_picking = {}  # lot_id -> picking_id
    lots_list = list(lot_ids)
    for i in range(0, len(lots_list), BATCH):
        batch = lots_list[i:i + BATCH]
        reception_mlines = odoo.search_read(
            'stock.move.line',
            [
                ['lot_id', 'in', batch],
                ['picking_id.picking_type_id.code', '=', 'incoming'],
                ['state', '=', 'done'],
            ],
            ['lot_id', 'picking_id', 'qty_done'],
            limit=50000,
        )
        for rml in reception_mlines:
            lid = rml['lot_id'][0] if isinstance(rml['lot_id'], list) else rml['lot_id']
            pid = rml['picking_id'][0] if isinstance(rml['picking_id'], list) else rml['picking_id']
            if lid not in lot_to_picking:
                lot_to_picking[lid] = pid

    print(f"  OK {len(lot_to_picking)} lotes con recepcion identificada")

    # Recolectar picking_ids unicos
    unique_picking_ids = list(set(lot_to_picking.values()))
    print(f"  Recepciones unicas: {len(unique_picking_ids)}")

    # ── 7. Cargar TODOS los campos de las recepciones unicas ─────────────────
    print("\n[7/8] Cargando informacion completa de recepciones...")

    # Campos completos de stock.picking
    PICKING_FIELDS = [
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
        'x_studio_patente_carro_na_si_no_aplica',
        'x_studio_rut_transportista',
        'x_studio_destino',
        'x_studio_bodega_destino',
        'x_studio_origen',
        'x_studio_actividad',
        'x_studio_mp',
        'x_studio_con_pallet_1si_0_no',
        'x_studio_nmero_de_operarios',
        'x_studio_nmero_bandeja_verde_45x34',
        'x_studio_nmero_de_bandeja_18_50x30',
        'x_studio_nmero_de_bandeja_iqf_60x40',
        'x_studio_hora_inicio_de_proceso',
        'x_studio_hora_termino_de_proceso',
        'x_studio_horas_de_detencin',
        'x_studio_tiene_calidad',
        'x_studio_se_ingresaron_pallets',
        'x_studio_se_ingreso_el_peso_neto',
        'x_studio_fecha_de_qc',
        'x_studio_es_transferencia_interna',
        'x_studio_load_id',
        # SII fields
        'sii_Patente', 'sii_date',
    ]

    all_pickings = []
    for i in range(0, len(unique_picking_ids), BATCH):
        batch = unique_picking_ids[i:i + BATCH]
        picks = odoo.search_read(
            'stock.picking',
            [['id', 'in', batch]],
            PICKING_FIELDS,
            limit=5000,
        )
        all_pickings.extend(picks)
        print(f"    Batch {i // BATCH + 1}: {len(picks)} recepciones cargadas")

    pick_map = {p['id']: p for p in all_pickings}
    print(f"  OK {len(all_pickings)} recepciones con datos completos")

    # Cargar OCs (purchase.order) vinculadas
    origins = set()
    for p in all_pickings:
        o = p.get('origin', '')
        if o:
            origins.add(o)

    oc_map = {}
    if origins:
        origins_list = list(origins)
        for i in range(0, len(origins_list), BATCH):
            batch = origins_list[i:i + BATCH]
            domain = ['|'] * (len(batch) - 1) if len(batch) > 1 else []
            for o in batch:
                domain.append(['name', '=', o])
            ocs = odoo.search_read(
                'purchase.order',
                domain,
                ['id', 'name', 'create_uid', 'partner_id', 'date_order',
                 'state', 'amount_total', 'currency_id'],
                limit=5000,
            )
            for oc in ocs:
                oc_map[oc['name']] = oc

    print(f"  OK {len(oc_map)} ordenes de compra cargadas")

    # ── 8. Construir Excel ───────────────────────────────────────────────────
    print("\n[8/8] Construyendo Excel...")
    import pandas as pd

    # === HOJA 1: Fabricaciones + Pallets Consumidos ===
    fab_rows = []
    for ml in all_mlines:
        mid = ml['move_id'][0] if isinstance(ml['move_id'], list) else ml['move_id']
        move = move_map.get(mid, {})
        fab_id = move_to_fab.get(mid)
        fab = fab_map.get(fab_id, {}) if fab_id else {}

        # Lot info
        lot_id_val = None
        lot_name = ''
        if ml.get('lot_id') and ml['lot_id']:
            lot_id_val = ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id']
            lot_name = ml['lot_id'][1] if isinstance(ml['lot_id'], list) else ''
        elif ml.get('lot_name'):
            lot_name = ml['lot_name']

        # Reception info
        pick_id = lot_to_picking.get(lot_id_val) if lot_id_val else None
        pick = pick_map.get(pick_id, {}) if pick_id else {}

        # OC info
        origin = pick.get('origin', '') or ''
        oc = oc_map.get(origin, {})
        creador_oc = safe_m2o(oc.get('create_uid', '')) if oc else ''

        # Dates
        fab_fecha = fab.get('x_studio_inicio_de_proceso', '') or fab.get('date_start', '') or ''
        mes_fab, dia_fab = parse_date_parts(fab_fecha)
        fecha_rec = pick.get('date_done', '') or pick.get('x_studio_fecha_de_ingreso', '') or ''
        mes_rec, dia_rec = parse_date_parts(fecha_rec)

        # quantity_done from stock.move (as user requested)
        qty_done_move = move.get('quantity_done', 0) or 0
        qty_done_line = ml.get('qty_done', 0) or 0

        fab_rows.append({
            # Fabricacion
            'Fabricacion': fab.get('name', ''),
            'Estado Fabricacion': fab.get('state', ''),
            'Producto Fabricado': safe_m2o(fab.get('product_id', '')),
            'Qty a Producir': fab.get('product_qty', 0) or 0,
            'Inicio Proceso': fab.get('x_studio_inicio_de_proceso', '') or '',
            'Termino Proceso': fab.get('x_studio_termino_de_proceso', '') or '',
            'Fecha Inicio': fab.get('date_start', '') or '',
            'Mes Fab': mes_fab,
            'Dia Fab': dia_fab,
            'Sala Proceso': fab.get('x_studio_sala_de_proceso', '') or '',
            'Dotacion': fab.get('x_studio_dotacin', 0) or 0,
            'HH': fab.get('x_studio_hh', 0) or 0,
            'HH Efectiva': fab.get('x_studio_hh_efectiva', 0) or 0,
            'Kg/HH Efectiva': fab.get('x_studio_kghh_efectiva', 0) or 0,
            'Horas Detencion': fab.get('x_studio_horas_de_detencin', 0) or 0,
            'PO Cliente': fab.get('x_studio_po_cliente_1', '') or '',
            'Numero PO': fab.get('x_studio_nmero_de_po_1', '') or '',
            'SO Asociada': fab.get('x_studio_po_asociada', '') or '',
            'Creador Fab': safe_m2o(fab.get('create_uid', '')),
            'Origen Fab': fab.get('origin', '') or '',
            # Componente consumido
            'Componente': safe_m2o(ml.get('product_id', '')),
            'Nombre Pallet': lot_name,
            'Qty Done (move)': qty_done_move,
            'Qty Done (linea)': qty_done_line,
            'Precio Unit': ml.get('x_studio_precio_unitario', 0) or 0,
            'Costo': ml.get('x_studio_coste', 0) or 0,
            'Fecha Consumo': ml.get('date', '') or '',
            # Recepcion de origen del pallet
            'Albaran Recepcion': pick.get('name', ''),
            'OC': origin,
            'Creador OC': creador_oc,
            'Productor': safe_m2o(pick.get('partner_id', '')),
            'Guia Despacho': pick.get('x_studio_gua_de_despacho', '') or '',
            'Acopio': pick.get('x_studio_acopio', '') or '',
            'Categoria Producto': pick.get('x_studio_categora_de_producto', '') or '',
            'Precio Kg Recep': pick.get('x_studio_precio_kg', 0) or 0,
            'Fecha Recepcion': fecha_rec,
            'Mes Rec': mes_rec,
            'Dia Rec': dia_rec,
        })

    df_fab = pd.DataFrame(fab_rows)
    if not df_fab.empty:
        df_fab.sort_values(['Fabricacion', 'Nombre Pallet'], inplace=True)

    # === HOJA 2: Recepciones Unicas con TODOS los campos ===
    rec_rows = []
    for p in all_pickings:
        fecha_ref = p.get('date_done', '') or p.get('x_studio_fecha_de_ingreso', '') or p.get('scheduled_date', '')
        mes, dia = parse_date_parts(fecha_ref)

        origin = p.get('origin', '') or ''
        oc = oc_map.get(origin, {})
        creador_oc = safe_m2o(oc.get('create_uid', '')) if oc else ''

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
            'Kg Netos': p.get('x_studio_kg_netos', 0) or 0,
            'Kg Brutos (char)': p.get('x_studio_kg_brutos', '') or '',
            'Kg Brutos (float)': p.get('x_studio_kg_brutos_1', 0) or 0,
            'Kg Hechos': p.get('x_studio_kg_hechos', 0) or 0,
            'Calidad': p.get('x_studio_calidad', '') or '',
            'Tiene Calidad': p.get('x_studio_tiene_calidad', False),
            'Fecha QC': p.get('x_studio_fecha_de_qc', '') or '',
            'Conductor': p.get('x_studio_nombre_conductor', '') or '',
            'RUT Conductor': p.get('x_studio_rut_transportista', '') or '',
            'Patente Camion': p.get('x_studio_patente_camion', '') or '',
            'Patente Carro': p.get('x_studio_patente_carro_na_si_no_aplica', '') or '',
            'SII Patente': p.get('sii_Patente', '') or '',
            'SII Fecha': p.get('sii_date', '') or '',
            'Destino': p.get('x_studio_destino', '') or '',
            'Bodega Destino': p.get('x_studio_bodega_destino', '') or '',
            'Origen Picking': p.get('x_studio_origen', '') or '',
            'Actividad': p.get('x_studio_actividad', '') or '',
            'MP': p.get('x_studio_mp', '') or '',
            'Con Pallet (1si 0no)': p.get('x_studio_con_pallet_1si_0_no', 0) or 0,
            'Num Operarios': p.get('x_studio_nmero_de_operarios', 0) or 0,
            'Bandejas Verde 45x34': p.get('x_studio_nmero_bandeja_verde_45x34', 0) or 0,
            'Bandejas 1/8 50x30': p.get('x_studio_nmero_de_bandeja_18_50x30', 0) or 0,
            'Bandejas IQF 60x40': p.get('x_studio_nmero_de_bandeja_iqf_60x40', 0) or 0,
            'Hora Inicio Proceso': p.get('x_studio_hora_inicio_de_proceso', '') or '',
            'Hora Termino Proceso': p.get('x_studio_hora_termino_de_proceso', '') or '',
            'Horas Detencion': p.get('x_studio_horas_de_detencin', 0) or 0,
            'Se Ingresaron Pallets': p.get('x_studio_se_ingresaron_pallets', False),
            'Se Ingreso Peso Neto': p.get('x_studio_se_ingreso_el_peso_neto', False),
            'Es Transferencia Interna': p.get('x_studio_es_transferencia_interna', False),
            'Load ID': p.get('x_studio_load_id', 0) or 0,
            'Tipo Operacion': safe_m2o(p.get('picking_type_id', '')),
        })

    df_rec = pd.DataFrame(rec_rows)
    if not df_rec.empty:
        df_rec.sort_values('Albaran', inplace=True)

    # === HOJA 3: Resumen ===
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        df_fab.to_excel(writer, sheet_name='Fabricaciones y Pallets', index=False)
        df_rec.to_excel(writer, sheet_name='Recepciones Unicas', index=False)

        total_fabs = len(fab_map)
        total_lineas = len(all_mlines)
        total_lotes = len(lot_ids)
        total_rec = len(all_pickings)
        total_kg_consumed = df_fab['Qty Done (linea)'].sum() if not df_fab.empty else 0

        resumen = pd.DataFrame({
            'Metrica': [
                'Producto Analizado',
                'Fecha Desde',
                'Total Fabricaciones',
                'Total Lineas de Consumo',
                'Lotes/Pallets Unicos',
                'Recepciones Unicas Vinculadas',
                'OCs Vinculadas',
                'Total Kg Consumidos (lineas)',
                'Fecha Reporte',
            ],
            'Valor': [
                ', '.join(product_names),
                FECHA_DESDE,
                total_fabs,
                total_lineas,
                total_lotes,
                total_rec,
                len(oc_map),
                f"{total_kg_consumed:,.2f}",
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ],
        })
        resumen.to_excel(writer, sheet_name='Resumen', index=False)

    print(f"\n{'=' * 80}")
    print(f"OK EXCEL GENERADO: {EXCEL_PATH}")
    print(f"  -> Hoja 'Fabricaciones y Pallets': {len(fab_rows)} filas")
    print(f"  -> Hoja 'Recepciones Unicas': {len(rec_rows)} recepciones")
    print(f"  -> Hoja 'Resumen'")
    print(f"  -> {total_fabs} fabricaciones | {total_lotes} lotes | {total_rec} recepciones")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
