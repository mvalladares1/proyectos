"""
Servicio de Trazabilidad de Pallets
Traza un pallet hacia atras mostrando cadenas de composicion en formato tabla:
  Pallet Origen | Cadena de Trazabilidad         | Guia Despacho | Productor
  044126        | 044126 -> 042950 -> 105255      | GD4300        | SOC. AGRICOLA
Muestrea 2-4 pallets consumidos por nivel.
"""
import logging
import random
from typing import Dict, List, Tuple, Optional, Any
from shared.odoo_client import OdooClient

logger = logging.getLogger(__name__)

MAX_DEPTH = 15
SAMPLE_FIRST = 4
SAMPLE_DEEP = 4


class TrazabilidadPalletService:

    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
        self._visited: set = set()

    # ================================================
    # PUBLICO
    # ================================================
    def trazar_pallet(self, pallet_name: str) -> Dict[str, Any]:
        self._visited = set()

        pkgs = self.odoo.search_read(
            "stock.quant.package",
            [("name", "=", pallet_name)],
            ["id", "name"], limit=1,
        )
        if not pkgs:
            return self._err(pallet_name, f"No se encontro el pallet '{pallet_name}'")

        pkg_id = pkgs[0]["id"]
        pkg_name = pkgs[0].get("name", pallet_name)

        # Encontrar orden de produccion del pack
        orden_id = self._find_production_order(pkg_id)
        if not orden_id:
            return self._err(pkg_name, f"'{pallet_name}' no tiene orden de produccion")

        # Pallets consumidos en esa orden
        all_consumidos = self._get_consumidos(orden_id)
        if not all_consumidos:
            return self._err(pkg_name, "La orden no tiene pallets consumidos")

        muestra = self._sample(all_consumidos, SAMPLE_FIRST)
        consumidos_str = " - ".join(self._short(n) for _, n in muestra)

        # Trazar cada pallet consumido
        cadenas: List[Dict] = []
        for c_id, c_name in muestra:
            paths: List[Dict] = []
            self._trazar_caminos(c_id, c_name, [self._short(c_name)], paths, 0)
            if not paths:
                cadenas.append({
                    "pallet_origen": self._short(c_name),
                    "cadena": "NO TIENE TRAZABILIDAD",
                    "guia_despacho": "",
                    "productor": "",
                })
            else:
                cadenas.extend(paths)

        return {
            "pack": pkg_name,
            "pallets_consumidos": consumidos_str,
            "cadenas": cadenas,
            "error": None,
        }

    # ================================================
    # RECURSION DE CAMINOS
    # ================================================
    def _trazar_caminos(
        self, pkg_id: int, pkg_name: str,
        path: List[str], result: List[Dict], depth: int,
    ):
        if depth > MAX_DEPTH or pkg_id in self._visited:
            return
        self._visited.add(pkg_id)

        orden_id = self._find_production_order(pkg_id)

        if not orden_id:
            # No fue producido -> hoja (recepcion o sin trazabilidad)
            recep = self._buscar_recepcion(pkg_id)
            if recep:
                result.append({
                    "pallet_origen": path[-1],
                    "cadena": " \u2192 ".join(path),
                    "guia_despacho": recep.get("guia_despacho", ""),
                    "productor": recep.get("proveedor", ""),
                })
            else:
                result.append({
                    "pallet_origen": path[-1],
                    "cadena": "NO TIENE TRAZABILIDAD",
                    "guia_despacho": "",
                    "productor": "",
                })
            return

        # Tiene orden de produccion -> buscar consumidos
        consumidos = self._get_consumidos(orden_id)
        if not consumidos:
            recep = self._buscar_recepcion(pkg_id)
            result.append({
                "pallet_origen": path[-1],
                "cadena": " \u2192 ".join(path),
                "guia_despacho": recep.get("guia_despacho", "") if recep else "",
                "productor": recep.get("proveedor", "") if recep else "",
            })
            return

        muestra = self._sample(consumidos, SAMPLE_DEEP)
        for c_id, c_name in muestra:
            self._trazar_caminos(
                c_id, c_name,
                path + [self._short(c_name)],
                result, depth + 1,
            )

    # ================================================
    # BUSCAR ORDEN DE PRODUCCION
    # =================================================
    def _find_production_order(self, pkg_id: int) -> Optional[int]:
        mls = self.odoo.search_read(
            "stock.move.line",
            [("result_package_id", "=", pkg_id),
             ("qty_done", ">", 0), ("state", "=", "done")],
            ["move_id"], limit=50,
        )
        if not mls:
            return None
        move_ids = list({self._m2o_id(m.get("move_id")) for m in mls if m.get("move_id")})
        if not move_ids:
            return None
        moves = self.odoo.search_read(
            "stock.move", [("id", "in", move_ids)],
            ["production_id", "raw_material_production_id"], limit=50,
        )
        for m in moves:
            pid = self._m2o_id(m.get("production_id"))
            if pid:
                return pid
        for m in moves:
            pid = self._m2o_id(m.get("raw_material_production_id"))
            if pid:
                return pid
        return None

    # ================================================
    # PALLETS CONSUMIDOS DE UNA ORDEN
    # ================================================
    def _get_consumidos(self, orden_id: int) -> List[Tuple[int, str]]:
        raw = self.odoo.search_read(
            "stock.move",
            [("raw_material_production_id", "=", orden_id)],
            ["id"], limit=500,
        )
        if not raw:
            return []
        raw_ids = [m["id"] for m in raw]
        cls = self.odoo.search_read(
            "stock.move.line",
            [("move_id", "in", raw_ids), ("package_id", "!=", False),
             ("qty_done", ">", 0), ("state", "=", "done")],
            ["package_id"], limit=500,
        )
        seen: Dict[int, str] = {}
        for c in cls:
            pid = self._m2o_id(c.get("package_id"))
            pnm = self._m2o_name(c.get("package_id"))
            if pid and pid not in seen:
                seen[pid] = pnm
        return list(seen.items())

    # =================================================
    # BUSCAR RECEPCION
    # =================================================
    def _buscar_recepcion(self, package_id: int) -> Optional[Dict]:
        try:
            mls = None
            for field in ("result_package_id", "package_id"):
                results = self.odoo.search_read(
                    "stock.move.line",
                    [(field, "=", package_id), ("state", "=", "done"),
                     ("picking_id", "!=", False)],
                    ["picking_id"], limit=50,
                )
                if results:
                    mls = results
                    break
            if not mls:
                return None

            pids = list({self._m2o_id(m.get("picking_id")) for m in mls if m.get("picking_id")})
            if not pids:
                return None

            picks = self.odoo.search_read(
                "stock.picking", [("id", "in", pids)],
                ["name", "partner_id", "x_studio_gua_de_despacho",
                 "date_done", "scheduled_date", "picking_type_id"],
                limit=50,
            )
            RECEP = [1, 217, 164]
            pick = None
            for p in picks:
                if self._m2o_id(p.get("picking_type_id")) in RECEP:
                    pick = p
                    break
            if not pick and picks:
                pick = picks[0]
            if not pick:
                return None

            return {
                "recepcion": pick.get("name", ""),
                "guia_despacho": str(pick.get("x_studio_gua_de_despacho", "") or ""),
                "proveedor": self._m2o_name(pick.get("partner_id")),
                "fecha": str(pick.get("date_done") or pick.get("scheduled_date") or ""),
            }
        except Exception as e:
            logger.error(f"Error recepcion {package_id}: {e}")
            return None

    # =================================================
    # UTILS
    # =================================================
    @staticmethod
    def _m2o_id(v) -> int:
        if isinstance(v, (list, tuple)) and v:
            return v[0]
        return v if isinstance(v, int) else 0

    @staticmethod
    def _m2o_name(v) -> str:
        if isinstance(v, (list, tuple)) and len(v) > 1:
            return v[1] or ""
        return ""

    @staticmethod
    def _short(name: str) -> str:
        """Strip PACK prefix: PACK0048229 -> 0048229"""
        if name.upper().startswith("PACK"):
            return name[4:]
        return name

    @staticmethod
    def _sample(items: list, n: int) -> list:
        if len(items) <= n:
            return items
        k = random.randint(2, n)
        return random.sample(items, min(k, len(items)))

    @staticmethod
    def _err(pack: str, msg: str) -> Dict:
        return {"pack": pack, "pallets_consumidos": "", "cadenas": [], "error": msg}
