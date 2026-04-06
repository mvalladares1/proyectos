"""
Genera una carpeta con detalle por partner y otra con consolidados de entradas/salidas
de bandejas a productor para analisis.

Fuente:
- Productos con categ_id = 107 (BANDEJAS A PRODUCTOR)
- Entradas: pickings incoming de RF/VILKUN/San Jose
- Salidas: pickings outgoing de RF/VILKUN/San Jose

Salida:
- output/bandejas_productores/analisis_bandejas_<timestamp>/detalle_partner/*.xlsx
- output/bandejas_productores/analisis_bandejas_<timestamp>/consolidado_analisis/consolidado_bandejas_analisis.xlsx
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

import pandas as pd
from openpyxl.styles import Font


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.odoo_client import OdooClient
from backend.services.recepcion_service import get_recepciones_mp


CATEGORIA_BANDEJAS_ID = 107
DEFAULT_FECHA_DESDE = "2025-11-01"
SALIDA_PICKING_TYPES = [2, 63, 194]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Exporta bandejas por partner y consolidado analitico.")
    parser.add_argument("--username", required=True, help="Usuario Odoo")
    parser.add_argument("--password", required=True, help="API key Odoo")
    parser.add_argument("--fecha-desde", default=DEFAULT_FECHA_DESDE, help="Fecha inicio YYYY-MM-DD")
    parser.add_argument(
        "--fecha-hasta",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Fecha fin YYYY-MM-DD",
    )
    return parser.parse_args()


def chunked(items: Sequence[int], size: int) -> Iterable[Sequence[int]]:
    for idx in range(0, len(items), size):
        yield items[idx: idx + size]


def fmt_m2o(value):
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return value[1]
    return value or ""


def fmt_m2o_id(value):
    if isinstance(value, (list, tuple)) and value:
        return value[0]
    return None


def safe_filename(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*]+', '_', name or 'SIN_NOMBRE').strip()
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned[:100] or 'SIN_NOMBRE'


def normalize_type_name(name: str) -> str:
    return (name or '').replace('Ã', 'A')


def infer_planta(picking_type_name: str) -> str:
    name = (picking_type_name or '').upper()
    if 'VILKUN' in name:
        return 'VILKUN'
    if 'SAN JOSE' in name:
        return 'SAN JOSE'
    if 'RIO FUTURO' in name or 'DELIVERY ORDERS' in name or 'RECEPCIONES MP' in name:
        return 'RIO FUTURO'
    return 'OTRO'


def infer_tipo_movimiento(picking_type_id: int) -> str:
    if picking_type_id in SALIDA_PICKING_TYPES:
        return 'salida'
    return 'entrada'


def infer_estado_bandeja(product_code: str, product_name: str) -> str:
    code = (product_code or '').strip().upper()
    name = (product_name or '').upper()
    if code.endswith('L') or 'LIMPIA' in name:
        return 'Limpia'
    return 'Sucia'


def clean_tipo_bandeja(product_name: str) -> str:
    name = product_name or ''
    name = re.sub(r'^\[.*?\]\s*', '', name)
    name = re.sub(r'\s*\(A PRODUCTOR\)', '', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*-\s*(SUCIA|LIMPIA|COPIA).*$','', name, flags=re.IGNORECASE)
    name = re.sub(r'\s*\(PRODUCTOR\).*$','', name, flags=re.IGNORECASE)
    return name.strip()


def build_output_dirs(fecha_desde: str, fecha_hasta: str) -> Dict[str, Path]:
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    root = PROJECT_ROOT / 'output' / 'bandejas_productores' / f'analisis_bandejas_{fecha_desde}_{fecha_hasta}_{timestamp}'
    partner_dir = root / 'detalle_partner'
    consolidated_dir = root / 'consolidado_analisis'
    partner_dir.mkdir(parents=True, exist_ok=True)
    consolidated_dir.mkdir(parents=True, exist_ok=True)
    return {'root': root, 'partner': partner_dir, 'consolidated': consolidated_dir}


def fetch_salidas(odoo: OdooClient, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
    move_fields = [
        'id', 'date', 'name', 'state', 'picking_id', 'picking_type_id', 'product_id',
        'product_uom', 'product_uom_qty', 'quantity_done', 'location_id', 'location_dest_id'
    ]
    domain = [
        ['product_id.categ_id', '=', CATEGORIA_BANDEJAS_ID],
        ['state', '=', 'done'],
        ['picking_id', '!=', False],
        ['date', '>=', f'{fecha_desde} 00:00:00'],
        ['date', '<=', f'{fecha_hasta} 23:59:59'],
        ['picking_type_id', 'in', SALIDA_PICKING_TYPES],
    ]

    result: List[Dict] = []
    ids = odoo.search('stock.move', domain, order='date asc')
    for batch in chunked(ids, 500):
        result.extend(odoo.search_read('stock.move', [['id', 'in', list(batch)]], move_fields))
    return result


def fetch_entradas_recepciones(username: str, password: str, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
    return get_recepciones_mp(
        username=username,
        password=password,
        fecha_inicio=fecha_desde,
        fecha_fin=fecha_hasta,
        solo_hechas=True,
        origen=['RFP', 'VILKUN', 'SAN JOSE'],
    )


def fetch_pickings(odoo: OdooClient, picking_ids: Sequence[int]) -> Dict[int, Dict]:
    picking_fields = [
        'id', 'name', 'origin', 'state', 'partner_id', 'create_date', 'scheduled_date', 'date_done',
        'location_id', 'location_dest_id', 'picking_type_id', 'x_studio_categora_de_producto',
        'x_studio_gua_de_despacho', 'x_studio_fecha_de_emisin_gdd'
    ]
    result: Dict[int, Dict] = {}
    for batch in chunked(list(picking_ids), 500):
        for row in odoo.search_read('stock.picking', [['id', 'in', list(batch)]], picking_fields):
            result[row['id']] = row
    return result


def fetch_products(odoo: OdooClient, product_ids: Sequence[int]) -> Dict[int, Dict]:
    result: Dict[int, Dict] = {}
    fields = ['id', 'name', 'default_code', 'categ_id']
    for batch in chunked(list(product_ids), 500):
        for row in odoo.search_read('product.product', [['id', 'in', list(batch)]], fields):
            result[row['id']] = row
    return result


def build_entradas_dataframe(recepciones: List[Dict]) -> pd.DataFrame:
    rows: List[Dict] = []

    for recepcion in recepciones:
        productos = recepcion.get('productos', []) or []
        for producto in productos:
            categoria = (producto.get('Categoria') or '').upper().strip()
            if categoria != 'BANDEJAS':
                continue

            cantidad = float(producto.get('Kg Hechos') or 0)
            if cantidad <= 0:
                continue

            product_name = producto.get('Producto') or ''
            rows.append(
                {
                    'tipo_movimiento': 'entrada',
                    'planta': recepcion.get('origen') or 'OTRO',
                    'picking_type_id': None,
                    'picking_type': f"{recepcion.get('origen') or 'OTRO'}: Recepciones MP",
                    'picking_id': recepcion.get('id'),
                    'picking': recepcion.get('albaran') or '',
                    'partner_id': None,
                    'partner': recepcion.get('productor') or 'SIN PARTNER',
                    'fecha_move': recepcion.get('fecha') or '',
                    'fecha_hecho': recepcion.get('fecha') or '',
                    'fecha_programada': recepcion.get('fecha') or '',
                    'fecha_creacion': '',
                    'origin': recepcion.get('oc_asociada') or '',
                    'estado_picking': recepcion.get('state') or '',
                    'categoria_picking': 'MP',
                    'guia_despacho': recepcion.get('guia_despacho') or '',
                    'fecha_emision_gdd': '',
                    'move_id': None,
                    'move_nombre': product_name,
                    'producto_id': producto.get('product_id'),
                    'producto_codigo': '',
                    'producto': product_name,
                    'tipo_bandeja': clean_tipo_bandeja(product_name),
                    'estado_bandeja': infer_estado_bandeja('', product_name),
                    'categoria_producto': categoria,
                    'unidad_medida': producto.get('UOM') or '',
                    'cantidad_planificada': cantidad,
                    'cantidad_hecha': cantidad,
                    'ubicacion_origen': '',
                    'ubicacion_destino': '',
                }
            )

    return pd.DataFrame(rows)


def build_movements_dataframe(moves: List[Dict], pickings: Dict[int, Dict], products: Dict[int, Dict]) -> pd.DataFrame:
    rows: List[Dict] = []

    for move in sorted(moves, key=lambda item: (item.get('date') or '', item.get('id') or 0)):
        picking_id = fmt_m2o_id(move.get('picking_id'))
        product_id = fmt_m2o_id(move.get('product_id'))
        picking = pickings.get(picking_id, {})
        product = products.get(product_id, {})
        picking_type_id = fmt_m2o_id(move.get('picking_type_id')) or fmt_m2o_id(picking.get('picking_type_id')) or 0
        picking_type_name = fmt_m2o(move.get('picking_type_id')) or fmt_m2o(picking.get('picking_type_id'))
        qty_done = float(move.get('quantity_done') or move.get('product_uom_qty') or 0)
        product_code = product.get('default_code') or ''
        product_name = fmt_m2o(move.get('product_id')) or product.get('name') or ''

        rows.append(
            {
                'tipo_movimiento': infer_tipo_movimiento(picking_type_id),
                'planta': infer_planta(picking_type_name),
                'picking_type_id': picking_type_id,
                'picking_type': picking_type_name,
                'picking_id': picking_id,
                'picking': picking.get('name') or fmt_m2o(move.get('picking_id')),
                'partner_id': fmt_m2o_id(picking.get('partner_id')),
                'partner': fmt_m2o(picking.get('partner_id')) or 'SIN PARTNER',
                'fecha_move': move.get('date'),
                'fecha_hecho': picking.get('date_done') or '',
                'fecha_programada': picking.get('scheduled_date') or '',
                'fecha_creacion': picking.get('create_date') or '',
                'origin': picking.get('origin') or '',
                'estado_picking': picking.get('state') or '',
                'categoria_picking': picking.get('x_studio_categora_de_producto') or '',
                'guia_despacho': picking.get('x_studio_gua_de_despacho') or '',
                'fecha_emision_gdd': picking.get('x_studio_fecha_de_emisin_gdd') or '',
                'move_id': move.get('id'),
                'move_nombre': move.get('name') or '',
                'producto_id': product_id,
                'producto_codigo': product_code,
                'producto': product_name,
                'tipo_bandeja': clean_tipo_bandeja(product_name),
                'estado_bandeja': infer_estado_bandeja(product_code, product_name),
                'categoria_producto': fmt_m2o(product.get('categ_id')),
                'unidad_medida': fmt_m2o(move.get('product_uom')),
                'cantidad_planificada': float(move.get('product_uom_qty') or 0),
                'cantidad_hecha': qty_done,
                'ubicacion_origen': fmt_m2o(move.get('location_id')) or fmt_m2o(picking.get('location_id')),
                'ubicacion_destino': fmt_m2o(move.get('location_dest_id')) or fmt_m2o(picking.get('location_dest_id')),
            }
        )

    return pd.DataFrame(rows)


def build_summary_sheets(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    summaries: Dict[str, pd.DataFrame] = {}

    if df.empty:
        empty = pd.DataFrame()
        return {
            'movimientos': empty,
            'entradas': empty,
            'salidas': empty,
            'resumen_partner': empty,
            'resumen_partner_producto': empty,
            'resumen_mensual': empty,
        }

    work_df = df.copy()
    work_df['fecha_base'] = pd.to_datetime(work_df['fecha_hecho'].fillna(''))
    work_df['periodo'] = work_df['fecha_base'].dt.strftime('%Y-%m').fillna('SIN_FECHA')

    entradas = work_df[work_df['tipo_movimiento'] == 'entrada'].copy()
    salidas = work_df[work_df['tipo_movimiento'] == 'salida'].copy()

    resumen_partner = (
        work_df.groupby(['partner', 'tipo_movimiento'], dropna=False)['cantidad_hecha']
        .sum()
        .reset_index()
        .pivot(index='partner', columns='tipo_movimiento', values='cantidad_hecha')
        .fillna(0)
        .reset_index()
    )
    if 'entrada' not in resumen_partner.columns:
        resumen_partner['entrada'] = 0.0
    if 'salida' not in resumen_partner.columns:
        resumen_partner['salida'] = 0.0
    resumen_partner['diferencia'] = resumen_partner['entrada'] - resumen_partner['salida']
    resumen_partner = resumen_partner.sort_values(['salida', 'entrada', 'partner'], ascending=[False, False, True])

    resumen_partner_producto = (
        work_df.groupby(['partner', 'tipo_movimiento', 'producto_codigo', 'producto', 'tipo_bandeja', 'estado_bandeja'], dropna=False)
        .agg(
            cantidad_total=('cantidad_hecha', 'sum'),
            pickings=('picking_id', 'nunique'),
            movimientos=('move_id', 'nunique'),
            primera_fecha=('fecha_hecho', 'min'),
            ultima_fecha=('fecha_hecho', 'max'),
        )
        .reset_index()
        .sort_values(['partner', 'tipo_movimiento', 'cantidad_total'], ascending=[True, True, False])
    )

    resumen_mensual = (
        work_df.groupby(['periodo', 'planta', 'tipo_movimiento'], dropna=False)['cantidad_hecha']
        .sum()
        .reset_index()
        .pivot(index=['periodo', 'planta'], columns='tipo_movimiento', values='cantidad_hecha')
        .fillna(0)
        .reset_index()
    )
    if 'entrada' not in resumen_mensual.columns:
        resumen_mensual['entrada'] = 0.0
    if 'salida' not in resumen_mensual.columns:
        resumen_mensual['salida'] = 0.0
    resumen_mensual['diferencia'] = resumen_mensual['entrada'] - resumen_mensual['salida']
    resumen_mensual = resumen_mensual.sort_values(['periodo', 'planta'])

    summaries['movimientos'] = work_df.drop(columns=['fecha_base'])
    summaries['entradas'] = entradas.drop(columns=['fecha_base'])
    summaries['salidas'] = salidas.drop(columns=['fecha_base'])
    summaries['resumen_partner'] = resumen_partner
    summaries['resumen_partner_producto'] = resumen_partner_producto
    summaries['resumen_mensual'] = resumen_mensual
    return summaries


def autosize_worksheet(worksheet) -> None:
    for column_cells in worksheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = '' if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 45)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)


def write_workbook(path: Path, sheets: Dict[str, pd.DataFrame]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine='openpyxl') as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            autosize_worksheet(writer.sheets[sheet_name[:31]])


def create_partner_files(df: pd.DataFrame, partner_dir: Path) -> int:
    count = 0
    for partner_name, partner_df in df.groupby('partner', dropna=False):
        partner_df = partner_df.sort_values(['fecha_hecho', 'tipo_movimiento', 'producto'], ascending=[False, True, True])
        summary = build_summary_sheets(partner_df)
        out_path = partner_dir / f"Bandejas_{safe_filename(str(partner_name))}.xlsx"
        write_workbook(
            out_path,
            {
                'movimientos': summary['movimientos'],
                'resumen_partner_producto': summary['resumen_partner_producto'],
                'resumen_mensual': summary['resumen_mensual'],
            },
        )
        count += 1
    return count


def main() -> None:
    args = parse_args()
    output_dirs = build_output_dirs(args.fecha_desde, args.fecha_hasta)

    print('=' * 100)
    print('EXPORTACION BANDEJAS POR PARTNER Y CONSOLIDADO')
    print('=' * 100)
    print(f'Periodo: {args.fecha_desde} -> {args.fecha_hasta}')
    print(f'Raiz salida: {output_dirs["root"]}')

    odoo = OdooClient(username=args.username, password=args.password)
    print('Conectado a Odoo')

    recepciones = fetch_entradas_recepciones(args.username, args.password, args.fecha_desde, args.fecha_hasta)
    print(f'Recepciones base obtenidas desde recepcion_service: {len(recepciones)}')

    moves = fetch_salidas(odoo, args.fecha_desde, args.fecha_hasta)
    print(f'Movimientos de salida obtenidos: {len(moves)}')

    picking_ids = sorted({fmt_m2o_id(row.get('picking_id')) for row in moves if row.get('picking_id')})
    product_ids = sorted({fmt_m2o_id(row.get('product_id')) for row in moves if row.get('product_id')})
    picking_ids = [row for row in picking_ids if row is not None]
    product_ids = [row for row in product_ids if row is not None]

    pickings = fetch_pickings(odoo, picking_ids)
    products = fetch_products(odoo, product_ids)
    entradas_df = build_entradas_dataframe(recepciones)
    salidas_df = build_movements_dataframe(moves, pickings, products)
    frames = [frame for frame in [entradas_df, salidas_df] if not frame.empty]
    if frames:
        all_columns = []
        for frame in frames:
            for column in frame.columns:
                if column not in all_columns:
                    all_columns.append(column)
        aligned_frames = [frame.reindex(columns=all_columns) for frame in frames]
        movements_df = pd.concat(aligned_frames, ignore_index=True, sort=False)
    else:
        movements_df = pd.DataFrame()
    print(f'Partners detectados: {movements_df["partner"].nunique()}')

    partner_files = create_partner_files(movements_df, output_dirs['partner'])
    print(f'Archivos partner generados: {partner_files}')

    consolidated_sheets = build_summary_sheets(movements_df)
    consolidated_path = output_dirs['consolidated'] / 'consolidado_bandejas_analisis.xlsx'
    write_workbook(consolidated_path, consolidated_sheets)

    metadata = pd.DataFrame(
        [
            {'metrica': 'fecha_desde', 'valor': args.fecha_desde},
            {'metrica': 'fecha_hasta', 'valor': args.fecha_hasta},
            {'metrica': 'categoria_bandejas_id', 'valor': CATEGORIA_BANDEJAS_ID},
            {'metrica': 'entrada_fuente', 'valor': 'backend.services.recepcion_service.get_recepciones_mp'},
            {'metrica': 'salida_picking_types', 'valor': ','.join(map(str, SALIDA_PICKING_TYPES))},
            {'metrica': 'movimientos_totales', 'valor': len(movements_df)},
            {'metrica': 'partners_unicos', 'valor': movements_df['partner'].nunique()},
            {'metrica': 'generado_en', 'valor': datetime.now().strftime('%Y-%m-%d %H:%M:%S')},
        ]
    )
    write_workbook(output_dirs['consolidated'] / 'metadata_exportacion.xlsx', {'metadata': metadata})

    print('Exportacion completada')
    print(f'Detalle partner: {output_dirs["partner"]}')
    print(f'Consolidado: {consolidated_path}')


if __name__ == '__main__':
    main()