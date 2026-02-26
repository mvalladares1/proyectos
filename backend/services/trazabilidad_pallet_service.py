"""
Servicio de Trazabilidad de Pallets v3
Muestra jerarquia de composicion:
  PACK X se conforma por A, B, C
    A se conforma por D, E
      D viene de recepcion (guia, productor)
"""
import logging
import random
from typing import Dict, List, Tuple, Optional, Any
from shared.odoo_client import OdooClient

logger = logging.getLogger(__name__)

MAX_DEPTH = 10
SAMPLE_N = 3


class TrazabilidadPalletService:

    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
        self._visited: set = set()

    def trazar_pallet(self, pallet_name: str) -> Dict[str, Any]:
        self._visited = set()

        pkg = self._find_package(pallet_name)
        if not pkg:
            return {"error": f"No se encontro el pallet '{pallet_name}'", "filas": []}

        filas: List[Dict] = []
        self._trazar_jerarquia(pkg["id"], pkg["name"], 0, filas)

        return {"error": None, "pack": pkg["name"], "filas": filas}

    def _trazar_jerarquia(self, pkg_id: int, pkg_name: str, nivel: int, filas: List[Dict]):
        if pkg_id in self._visited or nivel > MAX_DEPTH:
            return
        self._visited.add(pkg_id)

        short_name = self._short(pkg_name)
        mo = self._find_mo(pkg_id)

        if not mo:
            # HOJA: no fue producido, es recepcion
            recep = self._buscar_recepcion(pkg_id)
            producto = self._get_product(pkg_id)
            filas.append({
                "nivel": nivel,
                "pallet": short_name,
                "se_conforma_por": "(RECEPCION)",
                "producto": producto,
                "guia_despacho": recep.get("guia_despacho", "") if recep else "",
                "productor": recep.get("proveedor", "") if recep else "",
                "fecha_recepcion": recep.get("fecha", "") if recep else "",
            })
            return

        # Tiene orden de produccion
        consumidos = self._get_consumidos(mo["id"])
        if not consumidos:
            recep = self._buscar_recepcion(pkg_id)
            producto = self._get_product(pkg_id)
            filas.append({
                "nivel": nivel,
                "pallet": short_name,
                "se_conforma_por": "(SIN CONSUMIDOSY",
                "producto": producto,
                "guia_despacho": recep.get("guia_despacho", "") if recep else "",
                "productor": recep.get("proveedor", "") if recep else "",
                "fecha_recepcion": "",
            })
            return

        muestra = self._sample(consumidos, SAMPLE_N)
        consumidos_str = ", ".join(self._short(n) for _, n in muestra)
        producto = self._m2o_name(mo.get("product_id"))

        filas.append({
            "nivel": nivel,
            "pallet": short_name,
            "se_conforma_por": consumidos_str,
            "producto": producto,
            "guia_despacho": "",
            "productor": "",
            "fecha_recepcion": "",
        })

        # Trazar cada consumido
        for c_id, c_name in muestra:
            self._trazar_jerarquia(c_id, c_name, nivel + 1, filas)

    def _find_package(self, name: str) -> Optional[Dict]:
        recs = self.odoo.search_read(
            'stock.quant.package',
            [['name', '=', name]],
            ['id', 'name'],
            limit=1,
        )
        return recs[0] if recs else None

    def _find_mo(self, pkg_id: int) -> Optional[Dict]:
        sml = self.odoo.search_read(
            'stock.move.line',
            [['result_package_id', '=', pkg_id]],
            ['move_id'],
            limit=1,
        )
        if not sml:
            return None
        move_id = self._m2o_id(sml[0].get('move_id'))
        if not move_id:
            return None
        move = self.odoo.search_read(
            'stock.move',
            [['id', '=', move_id]],
            ['production_id'],
            limit=1,
        )
        if not move:
            return None
        mo_id = self._m2o_id(move[0].get('production_id'))
        if not mo_id:
            return None
        mos = self.odoo.search_read(
            'mrp.production',
            [['id', '=', mo_id]],
            ['id', 'name', 'product_id'],
            limit=1,
        )
        return mos[0] if mos else None

    def _get_consumidos(self, mo_id: int) -> List[Tuple[int, str]]:
        smls = self.odoo.search_read(
            'stock.move.line',
            [
                ['production_id', '=', mo_id],
                ['package_id', '!=', False],
                ['state', '=', 'done'],
            ],
            ['package_id'],
        )
        seen = {}
        for s in smls:
            pid = self._m2o_id(s.get('package_id'))
            pname = self._m2o_name(s.get('package_id'))
            if pid and pid not in seen:
                seen[pid] = pname or str(pid)
        return [(k, v) for k, v in seen.items()]

    def _get_product(self, pkg_id: int) -> str:
        quants = self.odoo.search_read(
            'stock.quant',
            [['package_id', '=', pkg_id]],
            ['product_id'],
            limit=1,
        )
        if not quants:
            return ''
        return self._m2o_name(quants[0].get('product_id')) or ''

    def _buscar_recepcion(self, pkg_id: int) -> Optional[Dict]:
        smls = self.odoo.search_read(
            'stock.move.line',
            [
                ['result_package_id', '=', pkg_id],
                ['state', '=', 'done'],
            ],
            ['picking_id'],
            limit=5,
        )
        for sml in smls:
            pick_id = self._m2o_id(sml.get('picking_id'))
            if not pick_id:
                continue
            picks = self.odoo.search_read(
                'stock.picking',
                [
                    ['id', '=', pick_id],
                    ['picking_type_id', 'in', [1, 217, 164]],
                ],
                ['id', 'name', 'x_studio_gua_de_despacho', 'partner_id', 'date_done'],
                limit=1,
            )
            if picks:
                p = picks[0]
                return {
                    'guia_despacho': p.get('x_studio_gua_de_despacho') or '',
                    'proveedor': self._m2o_name(p.get('partner_id')) or '',
                    'fecha': str(p.get('date_done') or '')[:10],
                }
        return None

    @staticmethod
    def _m2o_id(val) -> Optional[int]:
        if isinstance(val, (list, tuple)) and len(val) >= 1:
            return val[0]
        if isinstance(val, int):
            return val
        return None

    @staticmethod
    def _m2o_name(val) -> Optional[str]:
        if isinstance(val, (list, tuple)) and len(val) >= 2:
            return str(val[1])
        return None

    @staticmethod
    def _short(name: str) -> str:
        return name

    @staticmethod
    def _sample(lst: list, n: int) -> list:
        if len(lst) <= n:
            return lst
        return random.sample(lst, n)

