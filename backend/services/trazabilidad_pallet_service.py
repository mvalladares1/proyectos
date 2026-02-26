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