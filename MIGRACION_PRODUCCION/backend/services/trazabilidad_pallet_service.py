"""
Servicio de Trazabilidad de Pallets v4
Genera Excel con formato:
  Pack | Pallets Consumidos | Pallet Origen | Cadena de Trazabilidad | Guía Despacho | Productor

Algoritmo:
  1. Encontrar la OP del pack ingresado
  2. Obtener TODOS los pallets consumidos por esa OP
  3. Para CADA pallet consumido, trazar recursivamente:
     - Si no tiene OP  → buscar recepción → fin de cadena
     - Si tiene OP     → obtener sus consumidos → seguir trazando
  4. Cada camino que termine en recepción = 1 fila del Excel
"""
import logging
from typing import Dict, List, Tuple, Optional, Any
from shared.odoo_client import OdooClient

logger = logging.getLogger(__name__)

MAX_DEPTH = 10
MAX_FILAS = 200   # Límite de filas por pallet para no sobrecargar


class TrazabilidadPalletService:

    def __init__(self, username: str, password: str):
        self.odoo = OdooClient(username=username, password=password)
        self._fila_count = 0

    # ── API pública ──────────────────────────────────────────────

    def trazar_pallet(self, pallet_name: str) -> Dict[str, Any]:
        self._fila_count = 0
        truncado = False

        pkg = self._find_package(pallet_name)
        if not pkg:
            return {"error": f"No se encontró el pallet '{pallet_name}'", "filas": []}

        mo = self._find_mo(pkg["id"])
        if not mo:
            return {"error": f"'{pallet_name}' no tiene orden de producción", "filas": []}

        consumidos = self._get_consumidos(mo["id"])
        if not consumidos:
            return {"error": f"La OP de '{pallet_name}' no tiene pallets consumidos", "filas": []}

        consumidos_str = " - ".join(self._short(n) for _, n in consumidos)

        filas: List[Dict] = []
        for c_id, c_name in consumidos:
            if self._fila_count >= MAX_FILAS:
                truncado = True
                break

            visited: set = set()
            paths = self._trazar_caminos(c_id, c_name, [self._short(c_name)], visited, 0)

            if not paths:
                filas.append({
                    "pallet_origen": self._short(c_name),
                    "cadena": "NO TIENE TRAZABILIDAD",
                    "guia_despacho": "",
                    "productor": "",
                })
                self._fila_count += 1
            else:
                for p in paths:
                    if self._fila_count >= MAX_FILAS:
                        truncado = True
                        break
                    filas.append({
                        "pallet_origen": self._short(c_name),
                        "cadena": " \u2192 ".join(p["chain"]),
                        "guia_despacho": p["guia"],
                        "productor": p["productor"],
                    })
                    self._fila_count += 1

        return {
            "error": None,
            "pack": pkg["name"],
            "pallets_consumidos": consumidos_str,
            "filas": filas,
            "truncado": truncado,
        }

    # ── Recursión ────────────────────────────────────────────────

    def _trazar_caminos(
        self,
        pkg_id: int,
        pkg_name: str,
        chain: List[str],
        visited: set,
        depth: int,
    ) -> List[Dict]:
        """Traza recursivamente un pallet hacia atrás.
        Retorna lista de {chain: [str,...], guia: str, productor: str}.
        Cada elemento = un camino que termina en recepción."""
        if pkg_id in visited or depth > MAX_DEPTH:
            return []
        visited.add(pkg_id)

        mo = self._find_mo(pkg_id)
        if not mo:
            # Sin OP → buscar recepción (hoja del árbol)
            recep = self._buscar_recepcion(pkg_id)
            if recep:
                return [{"chain": chain, "guia": recep["guia_despacho"], "productor": recep["proveedor"]}]
            return []  # sin trazabilidad

        # Tiene OP → buscar qué pallets consumió
        consumidos = self._get_consumidos(mo["id"])
        if not consumidos:
            # OP sin consumos visibles → tratar como hoja
            recep = self._buscar_recepcion(pkg_id)
            if recep:
                return [{"chain": chain, "guia": recep["guia_despacho"], "productor": recep["proveedor"]}]
            return []

        results: List[Dict] = []
        for c_id, c_name in consumidos:
            new_chain = chain + [self._short(c_name)]
            sub = self._trazar_caminos(c_id, c_name, new_chain, visited, depth + 1)
            results.extend(sub)
        return results

    # ── Helpers Odoo ─────────────────────────────────────────────

    def _find_package(self, name: str) -> Optional[Dict]:
        recs = self.odoo.search_read(
            'stock.quant.package',
            [['name', '=', name]],
            ['id', 'name'],
            limit=1,
        )
        return recs[0] if recs else None

    def _find_mo(self, pkg_id: int) -> Optional[Dict]:
        """Encuentra la OP que produjo un pallet (result_package_id → move → production_id)."""
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
        """Obtiene TODOS los pallets consumidos por una OP (via raw_material_production_id)."""
        moves = self.odoo.search_read(
            'stock.move',
            [
                ['raw_material_production_id', '=', mo_id],
                ['state', '=', 'done'],
            ],
            ['id'],
        )
        if not moves:
            return []

        move_ids = [m['id'] for m in moves]
        smls = self.odoo.search_read(
            'stock.move.line',
            [
                ['move_id', 'in', move_ids],
                ['package_id', '!=', False],
            ],
            ['package_id'],
        )

        seen: Dict[int, str] = {}
        for s in smls:
            pid = self._m2o_id(s.get('package_id'))
            pname = self._m2o_name(s.get('package_id'))
            if pid and pid not in seen:
                seen[pid] = pname or str(pid)
        return [(k, v) for k, v in seen.items()]

    def _buscar_recepcion(self, pkg_id: int) -> Optional[Dict]:
        """Busca el picking de recepción donde llegó un pallet."""
        smls = self.odoo.search_read(
            'stock.move.line',
            [
                ['result_package_id', '=', pkg_id],
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

    # ── Utilidades ───────────────────────────────────────────────

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
        """Acorta nombre de pallet: PACK0048229 → 048229."""
        if not name:
            return ""
        n = name.strip()
        if n.upper().startswith("PACK"):
            rest = n[4:].strip()
            return rest if rest else n
        return n

