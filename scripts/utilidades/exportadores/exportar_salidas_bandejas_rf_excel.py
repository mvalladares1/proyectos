"""
Exporta a Excel las salidas de bandejas a productor de Rio Futuro.

Criterio principal:
- Transferencias completadas de Rio Futuro salida (stock.picking.type id 2)
- Fecha desde noviembre 2025 hasta hoy, configurable
- Se incluyen pickings que cumplan al menos uno de estos criterios:
  1. stock.picking.x_studio_categora_de_producto = BANDEJAS A PRODUCTOR
  2. Alguna linea stock.move tiene producto con categ_id = 107 (BANDEJAS A PRODUCTOR)

El archivo genera hojas de resumen por picking, detalle por linea y excepciones de filtro.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

import pandas as pd
from openpyxl.styles import Font


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from shared.odoo_client import OdooClient


PICKING_TYPE_ID_RF_OUT = 2
CATEGORIA_BANDEJAS_ID = 107
CATEGORIA_BANDEJAS_NOMBRE = "BANDEJAS A PRODUCTOR"
DEFAULT_FECHA_DESDE = "2025-11-01"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exporta salidas de bandejas a productor de Rio Futuro a Excel."
    )
    parser.add_argument("--username", required=True, help="Usuario Odoo")
    parser.add_argument("--password", required=True, help="API key Odoo")
    parser.add_argument("--fecha-desde", default=DEFAULT_FECHA_DESDE, help="Fecha inicio YYYY-MM-DD")
    parser.add_argument(
        "--fecha-hasta",
        default=datetime.now().strftime("%Y-%m-%d"),
        help="Fecha fin YYYY-MM-DD",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Ruta destino del Excel. Si se omite, se guarda en output/bandejas_productores/",
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


def build_output_path(requested_path: str, fecha_desde: str, fecha_hasta: str) -> Path:
    if requested_path:
        return Path(requested_path)

    output_dir = PROJECT_ROOT / "output" / "bandejas_productores"
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return output_dir / f"salidas_bandejas_rf_{fecha_desde}_{fecha_hasta}_{timestamp}.xlsx"


def fetch_pick_ids_by_field(odoo: OdooClient, fecha_desde: str, fecha_hasta: str) -> Set[int]:
    domain = [
        ["state", "=", "done"],
        ["date_done", ">=", f"{fecha_desde} 00:00:00"],
        ["date_done", "<=", f"{fecha_hasta} 23:59:59"],
        ["picking_type_id", "=", PICKING_TYPE_ID_RF_OUT],
        ["x_studio_categora_de_producto", "=", CATEGORIA_BANDEJAS_NOMBRE],
    ]
    return set(odoo.search("stock.picking", domain, order="date_done desc"))


def fetch_move_rows_by_product_category(odoo: OdooClient, fecha_desde: str, fecha_hasta: str) -> List[Dict]:
    domain = [
        ["state", "=", "done"],
        ["date", ">=", f"{fecha_desde} 00:00:00"],
        ["date", "<=", f"{fecha_hasta} 23:59:59"],
        ["picking_id", "!=", False],
        ["picking_type_id", "=", PICKING_TYPE_ID_RF_OUT],
        ["product_id.categ_id", "=", CATEGORIA_BANDEJAS_ID],
    ]
    move_ids = odoo.search("stock.move", domain, order="date desc")
    rows: List[Dict] = []

    move_fields = [
        "id",
        "date",
        "name",
        "state",
        "picking_id",
        "picking_type_id",
        "product_id",
        "product_uom",
        "product_uom_qty",
        "quantity_done",
        "location_id",
        "location_dest_id",
    ]

    for batch in chunked(move_ids, 500):
        rows.extend(odoo.search_read("stock.move", [["id", "in", list(batch)]], move_fields))
    return rows


def fetch_pickings(odoo: OdooClient, pick_ids: Sequence[int]) -> Dict[int, Dict]:
    picking_fields = [
        "id",
        "name",
        "origin",
        "state",
        "partner_id",
        "create_date",
        "scheduled_date",
        "date_done",
        "location_id",
        "location_dest_id",
        "picking_type_id",
        "x_studio_categora_de_producto",
        "x_studio_gua_de_despacho",
        "x_studio_fecha_de_emisin_gdd",
        "move_ids_without_package",
        "move_line_ids",
    ]
    result: Dict[int, Dict] = {}
    for batch in chunked(list(pick_ids), 500):
        rows = odoo.search_read("stock.picking", [["id", "in", list(batch)]], picking_fields)
        for row in rows:
            result[row["id"]] = row
    return result


def fetch_move_lines(odoo: OdooClient, move_ids: Sequence[int]) -> Dict[int, List[Dict]]:
    fields = [
        "id",
        "date",
        "move_id",
        "product_id",
        "qty_done",
        "lot_id",
        "package_id",
        "result_package_id",
        "owner_id",
        "location_id",
        "location_dest_id",
        "reference",
    ]
    grouped: Dict[int, List[Dict]] = defaultdict(list)
    for batch in chunked(list(move_ids), 500):
        rows = odoo.search_read("stock.move.line", [["move_id", "in", list(batch)]], fields)
        for row in rows:
            move_id = fmt_m2o_id(row.get("move_id"))
            if move_id:
                grouped[move_id].append(row)
    return grouped


def fetch_products(odoo: OdooClient, product_ids: Sequence[int]) -> Dict[int, Dict]:
    fields = ["id", "name", "default_code", "categ_id"]
    products: Dict[int, Dict] = {}
    for batch in chunked(list(product_ids), 500):
        rows = odoo.search_read("product.product", [["id", "in", list(batch)]], fields)
        for row in rows:
            products[row["id"]] = row
    return products


def build_pickings_dataframe(
    pickings: Dict[int, Dict],
    field_pick_ids: Set[int],
    line_pick_ids: Set[int],
    moves: List[Dict],
    move_lines_by_move: Dict[int, List[Dict]],
    products: Dict[int, Dict],
) -> pd.DataFrame:
    picks_metrics: Dict[int, Dict[str, float]] = defaultdict(lambda: {"moves": 0, "move_lines": 0, "qty_total": 0.0})

    for move in moves:
        pick_id = fmt_m2o_id(move.get("picking_id"))
        if not pick_id:
            continue
        picks_metrics[pick_id]["moves"] += 1
        picks_metrics[pick_id]["qty_total"] += float(move.get("quantity_done") or move.get("product_uom_qty") or 0)
        picks_metrics[pick_id]["move_lines"] += max(1, len(move_lines_by_move.get(move["id"], [])))

    rows = []
    for pick_id, pick in sorted(pickings.items(), key=lambda item: item[1].get("date_done") or ""):
        metrics = picks_metrics.get(pick_id, {})
        rows.append(
            {
                "picking_id": pick_id,
                "picking": pick.get("name", ""),
                "fecha_creacion": pick.get("create_date"),
                "fecha_programada": pick.get("scheduled_date"),
                "fecha_hecho": pick.get("date_done"),
                "partner": fmt_m2o(pick.get("partner_id")),
                "partner_id": fmt_m2o_id(pick.get("partner_id")),
                "origin": pick.get("origin") or "",
                "estado": pick.get("state") or "",
                "tipo_operacion": fmt_m2o(pick.get("picking_type_id")),
                "ubicacion_origen": fmt_m2o(pick.get("location_id")),
                "ubicacion_destino": fmt_m2o(pick.get("location_dest_id")),
                "categoria_picking": pick.get("x_studio_categora_de_producto") or "",
                "guia_despacho": pick.get("x_studio_gua_de_despacho") or "",
                "fecha_emision_gdd": pick.get("x_studio_fecha_de_emisin_gdd") or "",
                "match_campo_picking": pick_id in field_pick_ids,
                "match_linea_producto": pick_id in line_pick_ids,
                "criterio_match": ", ".join(
                    value
                    for ok, value in [
                        (pick_id in field_pick_ids, "campo_picking"),
                        (pick_id in line_pick_ids, "linea_producto"),
                    ]
                    if ok
                ),
                "movimientos_bandeja": int(metrics.get("moves", 0)),
                "lineas_bandeja": int(metrics.get("move_lines", 0)),
                "cantidad_total_bandejas": float(metrics.get("qty_total", 0.0)),
            }
        )

    return pd.DataFrame(rows)


def build_detail_dataframe(
    moves: List[Dict],
    pickings: Dict[int, Dict],
    move_lines_by_move: Dict[int, List[Dict]],
    products: Dict[int, Dict],
    field_pick_ids: Set[int],
    line_pick_ids: Set[int],
) -> pd.DataFrame:
    rows = []

    for move in sorted(moves, key=lambda row: (row.get("date") or "", row.get("id") or 0)):
        pick_id = fmt_m2o_id(move.get("picking_id"))
        product_id = fmt_m2o_id(move.get("product_id"))
        pick = pickings.get(pick_id, {})
        product = products.get(product_id, {})
        line_rows = move_lines_by_move.get(move["id"], [])

        base = {
            "picking_id": pick_id,
            "picking": fmt_m2o(move.get("picking_id")),
            "fecha_hecho_picking": pick.get("date_done"),
            "fecha_programada": pick.get("scheduled_date"),
            "partner": fmt_m2o(pick.get("partner_id")),
            "origin": pick.get("origin") or "",
            "tipo_operacion": fmt_m2o(pick.get("picking_type_id")),
            "categoria_picking": pick.get("x_studio_categora_de_producto") or "",
            "guia_despacho": pick.get("x_studio_gua_de_despacho") or "",
            "fecha_emision_gdd": pick.get("x_studio_fecha_de_emisin_gdd") or "",
            "move_id": move.get("id"),
            "move_fecha": move.get("date"),
            "move_nombre": move.get("name") or "",
            "producto_id": product_id,
            "producto_codigo": product.get("default_code") or "",
            "producto": fmt_m2o(move.get("product_id")),
            "categoria_producto": fmt_m2o(product.get("categ_id")),
            "unidad_medida": fmt_m2o(move.get("product_uom")),
            "cantidad_planificada": float(move.get("product_uom_qty") or 0),
            "cantidad_hecha_move": float(move.get("quantity_done") or 0),
            "ubicacion_origen": fmt_m2o(move.get("location_id")),
            "ubicacion_destino": fmt_m2o(move.get("location_dest_id")),
            "match_campo_picking": pick_id in field_pick_ids,
            "match_linea_producto": pick_id in line_pick_ids,
        }

        if not line_rows:
            rows.append(
                {
                    **base,
                    "move_line_id": None,
                    "move_line_fecha": "",
                    "cantidad_hecha_linea": float(move.get("quantity_done") or 0),
                    "lote": "",
                    "package_origen": "",
                    "package_resultado": "",
                    "owner": "",
                    "referencia": "",
                }
            )
            continue

        for line in line_rows:
            rows.append(
                {
                    **base,
                    "move_line_id": line.get("id"),
                    "move_line_fecha": line.get("date"),
                    "cantidad_hecha_linea": float(line.get("qty_done") or 0),
                    "lote": fmt_m2o(line.get("lot_id")),
                    "package_origen": fmt_m2o(line.get("package_id")),
                    "package_resultado": fmt_m2o(line.get("result_package_id")),
                    "owner": fmt_m2o(line.get("owner_id")),
                    "referencia": line.get("reference") or "",
                }
            )

    return pd.DataFrame(rows)


def build_partner_product_summary(detail_df: pd.DataFrame) -> pd.DataFrame:
    if detail_df.empty:
        return pd.DataFrame()

    grouped = (
        detail_df.groupby(["partner", "producto_codigo", "producto", "categoria_producto"], dropna=False)
        .agg(
            pickings=("picking_id", "nunique"),
            lineas=("move_line_id", "count"),
            cantidad_total=("cantidad_hecha_linea", "sum"),
            primera_fecha=("fecha_hecho_picking", "min"),
            ultima_fecha=("fecha_hecho_picking", "max"),
        )
        .reset_index()
        .sort_values(["partner", "cantidad_total", "producto"], ascending=[True, False, True])
    )
    return grouped


def build_exceptions_dataframe(pickings: Dict[int, Dict], only_field: Set[int], only_line: Set[int]) -> pd.DataFrame:
    rows = []
    for label, ids in (("solo_campo_picking", only_field), ("solo_linea_producto", only_line)):
        for pick_id in sorted(ids):
            pick = pickings.get(pick_id, {})
            rows.append(
                {
                    "tipo_excepcion": label,
                    "picking_id": pick_id,
                    "picking": pick.get("name", ""),
                    "fecha_hecho": pick.get("date_done"),
                    "partner": fmt_m2o(pick.get("partner_id")),
                    "origin": pick.get("origin") or "",
                    "tipo_operacion": fmt_m2o(pick.get("picking_type_id")),
                    "categoria_picking": pick.get("x_studio_categora_de_producto") or "",
                    "guia_despacho": pick.get("x_studio_gua_de_despacho") or "",
                }
            )
    return pd.DataFrame(rows)


def build_metadata_dataframe(
    fecha_desde: str,
    fecha_hasta: str,
    field_pick_ids: Set[int],
    line_pick_ids: Set[int],
    union_pick_ids: Set[int],
    moves: List[Dict],
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"metrica": "fecha_desde", "valor": fecha_desde},
            {"metrica": "fecha_hasta", "valor": fecha_hasta},
            {"metrica": "picking_type_id", "valor": PICKING_TYPE_ID_RF_OUT},
            {"metrica": "categoria_producto_id", "valor": CATEGORIA_BANDEJAS_ID},
            {"metrica": "categoria_producto_nombre", "valor": CATEGORIA_BANDEJAS_NOMBRE},
            {"metrica": "pickings_por_campo_picking", "valor": len(field_pick_ids)},
            {"metrica": "pickings_por_linea_producto", "valor": len(line_pick_ids)},
            {"metrica": "pickings_union_total", "valor": len(union_pick_ids)},
            {"metrica": "movimientos_categoria_107", "valor": len(moves)},
            {"metrica": "generado_en", "valor": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
        ]
    )


def autosize_worksheet(worksheet) -> None:
    for column_cells in worksheet.columns:
        max_length = 0
        column_letter = column_cells[0].column_letter
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        worksheet.column_dimensions[column_letter].width = min(max(max_length + 2, 12), 45)
    for cell in worksheet[1]:
        cell.font = Font(bold=True)


def write_excel(output_path: Path, sheets: Dict[str, pd.DataFrame]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, index=False, sheet_name=sheet_name)
            autosize_worksheet(writer.sheets[sheet_name])


def main() -> None:
    args = parse_args()
    output_path = build_output_path(args.output, args.fecha_desde, args.fecha_hasta)

    print("=" * 100)
    print("EXPORTACION SALIDAS DE BANDEJAS RIO FUTURO")
    print("=" * 100)
    print(f"Periodo: {args.fecha_desde} -> {args.fecha_hasta}")
    print(f"Salida: {output_path}")

    odoo = OdooClient(username=args.username, password=args.password)
    print("Conectado a Odoo")

    field_pick_ids = fetch_pick_ids_by_field(odoo, args.fecha_desde, args.fecha_hasta)
    print(f"Pickings por campo picking: {len(field_pick_ids)}")

    moves = fetch_move_rows_by_product_category(odoo, args.fecha_desde, args.fecha_hasta)
    line_pick_ids = {fmt_m2o_id(row.get("picking_id")) for row in moves if row.get("picking_id")}
    line_pick_ids.discard(None)
    print(f"Movimientos con productos categ_id=107: {len(moves)}")
    print(f"Pickings por linea de producto: {len(line_pick_ids)}")

    union_pick_ids = field_pick_ids | line_pick_ids
    only_field = field_pick_ids - line_pick_ids
    only_line = line_pick_ids - field_pick_ids
    print(f"Pickings union total: {len(union_pick_ids)}")
    print(f"Excepciones solo campo: {len(only_field)}")
    print(f"Excepciones solo linea: {len(only_line)}")

    pickings = fetch_pickings(odoo, sorted(union_pick_ids))
    move_ids = [row["id"] for row in moves]
    move_lines_by_move = fetch_move_lines(odoo, move_ids)
    product_ids = sorted({fmt_m2o_id(row.get("product_id")) for row in moves if row.get("product_id")})
    product_ids = [pid for pid in product_ids if pid is not None]
    products = fetch_products(odoo, product_ids)

    pickings_df = build_pickings_dataframe(
        pickings=pickings,
        field_pick_ids=field_pick_ids,
        line_pick_ids=line_pick_ids,
        moves=moves,
        move_lines_by_move=move_lines_by_move,
        products=products,
    ).sort_values(["fecha_hecho", "picking"], ascending=[False, True])

    detail_df = build_detail_dataframe(
        moves=moves,
        pickings=pickings,
        move_lines_by_move=move_lines_by_move,
        products=products,
        field_pick_ids=field_pick_ids,
        line_pick_ids=line_pick_ids,
    ).sort_values(["fecha_hecho_picking", "partner", "picking", "move_id", "move_line_id"], ascending=[False, True, True, True, True])

    partner_summary_df = build_partner_product_summary(detail_df)
    exceptions_df = build_exceptions_dataframe(pickings, only_field, only_line)
    metadata_df = build_metadata_dataframe(
        args.fecha_desde,
        args.fecha_hasta,
        field_pick_ids,
        line_pick_ids,
        union_pick_ids,
        moves,
    )

    write_excel(
        output_path,
        {
            "resumen": metadata_df,
            "pickings": pickings_df,
            "detalle_lineas": detail_df,
            "resumen_partner_producto": partner_summary_df,
            "excepciones": exceptions_df,
        },
    )

    print("Excel generado correctamente")
    print(f"Archivo: {output_path}")


if __name__ == "__main__":
    main()