"""
Review Forense: [1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK
==============================================================
Analiza todas las fabricaciones (mrp.production) que usan este producto,
extrae los pallets de componentes consumidos y genera un Excel con:
- Albarán (stock.picking)
- Productor (partner_id del picking de recepción)
- Guía de despacho
- Kg consumidos
- Precio
- Lote/Pallet
- Orden de fabricación
- Fecha
"""

import sys
import os
from datetime import datetime

# Agregar raíz del proyecto al path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

from shared.odoo_client import OdooClient

# --- Credenciales ---
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Directorio de salida
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXCEL_PATH = os.path.join(OUTPUT_DIR, f"forense_tunel_estatico_vlk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx")

BATCH = 200  # tamaño de batch para consultas


def safe_m2o(val):
    """Extrae nombre de un campo many2one."""
    if isinstance(val, list) and len(val) >= 2:
        return val[1]
    elif isinstance(val, (int, float)):
        return str(val)
    return str(val) if val else ''


def main():
    print("=" * 80)
    print("REVIEW FORENSE: [1.1.1] PROCESO CONGELADO TÚNEL ESTÁTICO VLK")
    print("=" * 80)

    # ── 1. Conectar ──────────────────────────────────────────────────────────
    print("\n[1/7] Conectando a Odoo...")
    odoo = OdooClient(username=USERNAME, password=PASSWORD, url=URL, db=DB)
    print("  ✓ Conectado\n")

    # ── 2. Buscar el producto ────────────────────────────────────────────────
    print("[2/7] Buscando producto...")
    productos = odoo.search_read(
        'product.product',
        [['name', 'ilike', 'PROCESO CONGELADO TÚNEL ESTÁTICO VLK']],
        ['id', 'name', 'default_code'],
    )
    if not productos:
        productos = odoo.search_read(
            'product.product',
            [['default_code', '=', '1.1.1']],
            ['id', 'name', 'default_code'],
        )
    if not productos:
        print("  ✗ Producto no encontrado. Abortando.")
        return

    for p in productos:
        print(f"  ✓ ID={p['id']}, Código={p.get('default_code','N/A')}, Nombre={p['name']}")
    product_ids = [p['id'] for p in productos]

    # ── 3. Buscar fabricaciones (mrp.production) ─────────────────────────────
    print(f"\n[3/7] Buscando fabricaciones...")
    fabricaciones = odoo.search_read(
        'mrp.production',
        [['product_id', 'in', product_ids]],
        [
            'id', 'name', 'state', 'product_id', 'product_qty',
            'qty_produced', 'date_start', 'date_finished',
            'origin', 'lot_producing_id',
            'x_studio_inicio_de_proceso', 'x_studio_termino_de_proceso',
            'x_studio_sala_de_proceso', 'x_studio_po_cliente_1',
            'x_studio_nmero_de_po_1',
        ],
        order='name asc',
    )

    print(f"  ✓ {len(fabricaciones)} fabricaciones encontradas")
    if not fabricaciones:
        print("  ✗ Sin fabricaciones. Abortando.")
        return

    # Mostrar resumen
    estados = {}
    for f in fabricaciones:
        estados[f['state']] = estados.get(f['state'], 0) + 1
    for st, cnt in estados.items():
        print(f"    {st}: {cnt}")

    fabricacion_ids = [f['id'] for f in fabricaciones]
    fab_map = {f['id']: f for f in fabricaciones}

    # ── 4. Obtener movimientos de componentes consumidos ─────────────────────
    print(f"\n[4/7] Obteniendo stock.move (componentes consumidos)...")

    all_moves = []
    for i in range(0, len(fabricacion_ids), BATCH):
        batch = fabricacion_ids[i:i + BATCH]
        moves = odoo.search_read(
            'stock.move',
            [
                ['raw_material_production_id', 'in', batch],
                ['state', '=', 'done'],
            ],
            [
                'id', 'product_id', 'product_uom_qty', 'quantity_done',
                'product_uom', 'raw_material_production_id', 'picking_id',
                'origin', 'reference', 'date', 'price_unit',
                'x_studio_precio_unitario', 'x_studio_costo',
                'x_studio_peso', 'x_studio_total',
            ],
        )
        all_moves.extend(moves)
        print(f"    Batch {i // BATCH + 1}: {len(moves)} movimientos")

    print(f"  ✓ Total: {len(all_moves)} movimientos de stock")
    move_map = {m['id']: m for m in all_moves}
    move_ids = [m['id'] for m in all_moves]

    # ── 5. Obtener stock.move.line (detalle por lote/pallet) ─────────────────
    print(f"\n[5/7] Obteniendo stock.move.line (detalle por lote)...")

    all_move_lines = []
    for i in range(0, len(move_ids), BATCH):
        batch = move_ids[i:i + BATCH]
        mlines = odoo.search_read(
            'stock.move.line',
            [['move_id', 'in', batch], ['state', '=', 'done']],
            [
                'id', 'move_id', 'product_id', 'lot_id', 'qty_done',
                'picking_id', 'date', 'reference',
                'origin', 'result_package_id',
                'x_studio_precio_unitario', 'x_studio_coste',
                'x_studio_reparto_de_costo',
            ],
        )
        all_move_lines.extend(mlines)
        print(f"    Batch {i // BATCH + 1}: {len(mlines)} líneas")

    print(f"  ✓ Total: {len(all_move_lines)} líneas de stock")

    # ── 6. Enriquecer con datos de lotes y pickings (recepciones) ────────────
    print(f"\n[6/7] Enriqueciendo datos de lotes y pickings...")

    # Recolectar IDs
    lot_ids = set()
    picking_ids = set()

    for ml in all_move_lines:
        if ml.get('lot_id') and ml['lot_id']:
            lot_ids.add(ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id'])
        if ml.get('picking_id') and ml['picking_id']:
            picking_ids.add(ml['picking_id'][0] if isinstance(ml['picking_id'], list) else ml['picking_id'])

    for m in all_moves:
        if m.get('picking_id') and m['picking_id']:
            picking_ids.add(m['picking_id'][0] if isinstance(m['picking_id'], list) else m['picking_id'])

    # Leer lotes
    lot_map = {}
    if lot_ids:
        lots_list = list(lot_ids)
        for i in range(0, len(lots_list), BATCH):
            batch = lots_list[i:i + BATCH]
            lots_data = odoo.search_read(
                'stock.lot',
                [['id', 'in', batch]],
                ['id', 'name', 'product_id'],
            )
            for lot in lots_data:
                lot_map[lot['id']] = lot
    print(f"  ✓ {len(lot_map)} lotes cargados")

    # Para cada lote, buscar su recepción original (picking de entrada)
    # Esto nos da productor, guía, precio, etc.
    print("  Buscando recepciones asociadas a los lotes...")

    # Buscar los move.lines de recepciones que usan estos lotes
    lot_reception_map = {}  # lot_id -> picking info
    if lot_ids:
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
                limit=5000,
            )
            for rml in reception_mlines:
                lid = rml['lot_id'][0] if isinstance(rml['lot_id'], list) else rml['lot_id']
                if lid not in lot_reception_map and rml.get('picking_id'):
                    pid = rml['picking_id'][0] if isinstance(rml['picking_id'], list) else rml['picking_id']
                    lot_reception_map[lid] = pid
                    picking_ids.add(pid)

    print(f"  ✓ {len(lot_reception_map)} lotes con recepción identificada")

    # Leer pickings (albaranes / recepciones)
    picking_map = {}
    if picking_ids:
        pickings_list = list(picking_ids)
        for i in range(0, len(pickings_list), BATCH):
            batch = pickings_list[i:i + BATCH]
            picks = odoo.search_read(
                'stock.picking',
                [['id', 'in', batch]],
                [
                    'id', 'name', 'origin', 'state', 'date_done',
                    'partner_id', 'picking_type_id',
                    'x_studio_gua_de_despacho',
                    'x_studio_precio_kg',
                    'x_studio_kg_netos',
                    'x_studio_kg_brutos',
                    'x_studio_acopio',
                    'x_studio_categora_de_producto',
                ],
            )
            for pk in picks:
                picking_map[pk['id']] = pk

    print(f"  ✓ {len(picking_map)} pickings cargados")

    # ── 7. Construir datos y exportar Excel ──────────────────────────────────
    print(f"\n[7/7] Construyendo Excel...")

    rows = []
    for ml in all_move_lines:
        move_id_val = ml['move_id'][0] if isinstance(ml['move_id'], list) else ml['move_id']
        move = move_map.get(move_id_val, {})

        fab_id = None
        if move.get('raw_material_production_id'):
            fab_id = move['raw_material_production_id'][0] if isinstance(move['raw_material_production_id'], list) else move['raw_material_production_id']
        fab = fab_map.get(fab_id, {})

        # Lot info
        lot_id_val = None
        if ml.get('lot_id') and ml['lot_id']:
            lot_id_val = ml['lot_id'][0] if isinstance(ml['lot_id'], list) else ml['lot_id']
        lot = lot_map.get(lot_id_val, {})

        # Picking de la fabricación (movimiento directo)
        fab_pick_id = None
        if ml.get('picking_id') and ml['picking_id']:
            fab_pick_id = ml['picking_id'][0] if isinstance(ml['picking_id'], list) else ml['picking_id']
        elif move.get('picking_id') and move['picking_id']:
            fab_pick_id = move['picking_id'][0] if isinstance(move['picking_id'], list) else move['picking_id']

        # Picking de recepción (donde entró el lote originalmente)
        rec_pick_id = lot_reception_map.get(lot_id_val)
        rec_pick = picking_map.get(rec_pick_id, {})

        # Picking de fabricación
        fab_pick = picking_map.get(fab_pick_id, {})

        row = {
            'Orden Fabricación': fab.get('name', ''),
            'Estado Fab.': fab.get('state', ''),
            'Fecha Inicio Fab.': fab.get('x_studio_inicio_de_proceso', '') or fab.get('date_start', ''),
            'Fecha Fin Fab.': fab.get('x_studio_termino_de_proceso', '') or fab.get('date_finished', ''),
            'Sala Proceso': fab.get('x_studio_sala_de_proceso', ''),
            'Origen Fab.': fab.get('origin', ''),
            'PO Cliente': fab.get('x_studio_po_cliente_1', ''),
            'Nro PO': fab.get('x_studio_nmero_de_po_1', ''),
            'Lote Producido': safe_m2o(fab.get('lot_producing_id', '')),
            'Producto Componente': safe_m2o(ml.get('product_id', '')),
            'Lote/Pallet': lot.get('name', '') or safe_m2o(ml.get('lot_id', '')),
            'Kg Consumidos': ml.get('qty_done', 0) or 0,
            'Precio Unit. (Mov.)': move.get('price_unit', 0) or move.get('x_studio_precio_unitario', 0) or 0,
            'Costo (Mov.)': move.get('x_studio_costo', 0) or 0,
            'Total Neto (Mov.)': move.get('x_studio_total', 0) or 0,
            # Datos de la recepción original del lote
            'Albarán Recepción': rec_pick.get('name', ''),
            'Productor': safe_m2o(rec_pick.get('partner_id', '')),
            'Guía Despacho': rec_pick.get('x_studio_gua_de_despacho', '') or '',
            'Precio Kg (Recepción)': rec_pick.get('x_studio_precio_kg', 0) or 0,
            'Kg Netos (Recepción)': rec_pick.get('x_studio_kg_netos', 0) or 0,
            'Kg Brutos (Recepción)': rec_pick.get('x_studio_kg_brutos', 0) or 0,
            'Acopio': rec_pick.get('x_studio_acopio', ''),
            'Categoría Producto': rec_pick.get('x_studio_categora_de_producto', ''),
            'Referencia Mov.': ml.get('reference', ''),
        }
        rows.append(row)

    if not rows:
        print("  No se encontraron move.lines, usando stock.move directamente...")
        for m in all_moves:
            fab_id = None
            if m.get('raw_material_production_id'):
                fab_id = m['raw_material_production_id'][0] if isinstance(m['raw_material_production_id'], list) else m['raw_material_production_id']
            fab = fab_map.get(fab_id, {})

            row = {
                'Orden Fabricación': fab.get('name', ''),
                'Estado Fab.': fab.get('state', ''),
                'Fecha Inicio Fab.': fab.get('date_start', ''),
                'Producto Componente': safe_m2o(m.get('product_id', '')),
                'Kg Consumidos': m.get('quantity_done', 0) or m.get('product_uom_qty', 0) or 0,
                'Precio Unit. (Mov.)': m.get('price_unit', 0) or 0,
                'Referencia Mov.': m.get('reference', ''),
            }
            rows.append(row)

    # Exportar con pandas
    import pandas as pd

    df = pd.DataFrame(rows)

    # Ordenar
    sort_cols = [c for c in ['Orden Fabricación', 'Lote/Pallet'] if c in df.columns]
    if sort_cols:
        df.sort_values(sort_cols, inplace=True)

    # Escribir Excel
    with pd.ExcelWriter(EXCEL_PATH, engine='openpyxl') as writer:
        # Hoja principal
        df.to_excel(writer, sheet_name='Componentes Consumidos', index=False)

        # Hoja resumen
        total_kg = df['Kg Consumidos'].sum() if 'Kg Consumidos' in df.columns else 0
        fab_states = df.groupby('Estado Fab.').size().to_dict() if 'Estado Fab.' in df.columns else {}

        resumen_data = {
            'Métrica': [
                'Total Fabricaciones',
                'Total Movimientos Consumo',
                'Total Líneas Detalle (por lote)',
                'Total Lotes Únicos',
                'Total Kg Consumidos',
                'Fabricaciones Hechas',
                'Fabricaciones Canceladas',
                'Fecha Generación Reporte',
            ],
            'Valor': [
                len(fabricaciones),
                len(all_moves),
                len(all_move_lines),
                len(lot_map),
                f"{total_kg:,.2f}",
                fab_states.get('done', 0),
                fab_states.get('cancel', 0),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            ],
        }
        pd.DataFrame(resumen_data).to_excel(writer, sheet_name='Resumen', index=False)

        # Hoja de fabricaciones
        fab_rows = []
        for f in fabricaciones:
            fab_rows.append({
                'ID': f['id'],
                'Nombre': f['name'],
                'Estado': f['state'],
                'Qty Producida': f.get('qty_produced', 0),
                'Qty Planeada': f.get('product_qty', 0),
                'Fecha Inicio': f.get('x_studio_inicio_de_proceso', '') or f.get('date_start', ''),
                'Fecha Fin': f.get('x_studio_termino_de_proceso', '') or f.get('date_finished', ''),
                'Sala': f.get('x_studio_sala_de_proceso', ''),
                'Origen': f.get('origin', ''),
                'PO Cliente': f.get('x_studio_po_cliente_1', ''),
                'Lote Producido': safe_m2o(f.get('lot_producing_id', '')),
            })
        pd.DataFrame(fab_rows).to_excel(writer, sheet_name='Fabricaciones', index=False)

    print(f"\n{'=' * 80}")
    print(f"✓ EXCEL GENERADO: {EXCEL_PATH}")
    print(f"  → Hojas: 'Componentes Consumidos', 'Resumen', 'Fabricaciones'")
    print(f"  → {len(rows)} filas de detalle")
    print(f"  → {len(fabricaciones)} fabricaciones")
    print(f"  → Total Kg consumidos: {total_kg:,.2f}")
    print(f"{'=' * 80}")


if __name__ == '__main__':
    main()
