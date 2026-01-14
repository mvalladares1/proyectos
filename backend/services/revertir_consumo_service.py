"""
Service: Revertir Consumo de Orden de Fabricación
Recupera MP a paquetes originales y elimina subproductos de desmontaje
"""
from typing import Dict, List
from shared.odoo_client import OdooClient


class RevertirConsumoService:
    def __init__(self, username: str, password: str, url: str = None, db: str = None):
        self.odoo = OdooClient(username=username, password=password, url=url, db=db)
    
    def preview_reversion_odf(self, odf_name: str) -> Dict:
        """
        Analiza lo que se haría al revertir una ODF SIN ejecutar cambios.
        
        Args:
            odf_name: Nombre de la orden (ej: VLK/CongTE109)
        
        Returns:
            Dict con preview detallado de acciones a realizar
        """
        # 1. Buscar la orden de fabricación
        mo = self._buscar_orden_fabricacion(odf_name)
        if not mo:
            return {
                "success": False,
                "message": f"❌ Orden de fabricación '{odf_name}' no encontrada"
            }
        
        mo_id = mo["id"]
        resultado = {
            "success": True,
            "message": f"✅ Análisis completado para {odf_name}",
            "odf_name": odf_name,
            "componentes_preview": [],
            "subproductos_preview": [],
            "transferencias_count": 0,
            "errores": []
        }
        
        # 2. Analizar componentes (sin crear transferencias)
        try:
            componentes_preview = self._analizar_componentes(mo_id)
            resultado["componentes_preview"] = componentes_preview["componentes"]
            resultado["transferencias_count"] = len(componentes_preview["componentes"])
            resultado["errores"].extend(componentes_preview.get("errores", []))
        except Exception as e:
            resultado["errores"].append(f"Error analizando componentes: {str(e)}")
        
        # 3. Analizar subproductos (sin modificar)
        try:
            subproductos_preview = self._analizar_subproductos(mo_id)
            resultado["subproductos_preview"] = subproductos_preview["subproductos"]
            resultado["errores"].extend(subproductos_preview.get("errores", []))
        except Exception as e:
            resultado["errores"].append(f"Error analizando subproductos: {str(e)}")
        
        return resultado
    
    def revertir_consumo_odf(self, odf_name: str) -> Dict:
        """
        Revierte el consumo de una ODF de desmontaje.
        
        Args:
            odf_name: Nombre de la orden (ej: VLK/CongTE109)
        
        Returns:
            Dict con resumen de operaciones realizadas
        """
        # 1. Buscar la orden de fabricación
        mo = self._buscar_orden_fabricacion(odf_name)
        if not mo:
            return {
                "success": False,
                "message": f"❌ Orden de fabricación '{odf_name}' no encontrada"
            }
        
        mo_id = mo["id"]
        resultado = {
            "success": True,
            "odf_name": odf_name,
            "componentes_revertidos": [],
            "subproductos_eliminados": [],
            "transferencias_creadas": [],
            "errores": []
        }
        
        # 2. Procesar componentes (recuperar MP a paquetes originales)
        try:
            componentes_result = self._revertir_componentes(mo_id, odf_name)
            resultado["componentes_revertidos"] = componentes_result["componentes"]
            resultado["transferencias_creadas"] = componentes_result["transferencias"]
            resultado["errores"].extend(componentes_result.get("errores", []))
        except Exception as e:
            resultado["errores"].append(f"Error procesando componentes: {str(e)}")
        
        # 3. Procesar subproductos (poner en 0)
        try:
            subproductos_result = self._eliminar_subproductos(mo_id)
            resultado["subproductos_eliminados"] = subproductos_result["subproductos"]
            resultado["errores"].extend(subproductos_result.get("errores", []))
        except Exception as e:
            resultado["errores"].append(f"Error procesando subproductos: {str(e)}")
        
        # 4. Construir mensaje de resumen
        if resultado["errores"]:
            resultado["success"] = False
            resultado["message"] = f"⚠️ Completado con {len(resultado['errores'])} errores"
        else:
            resultado["message"] = (
                f"✅ Reversión completada: "
                f"{len(resultado['componentes_revertidos'])} componentes recuperados, "
                f"{len(resultado['subproductos_eliminados'])} subproductos eliminados"
            )
        
        return resultado
    
    def _buscar_orden_fabricacion(self, odf_name: str) -> Dict:
        """Busca la orden de fabricación por nombre"""
        ordenes = self.odoo.search_read(
            "mrp.production",
            [("name", "=", odf_name)],
            ["id", "name", "state", "product_id"]
        )
        return ordenes[0] if ordenes else None
    
    def _analizar_componentes(self, mo_id: int) -> Dict:
        """
        Analiza componentes a recuperar SIN crear transferencias.
        Solo retorna información de lo que se haría.
        """
        resultado = {
            "componentes": [],
            "errores": []
        }
        
        # Buscar movimientos de consumo
        moves = self.odoo.search_read(
            "stock.move",
            [
                ("raw_material_production_id", "=", mo_id),
                ("state", "=", "done")
            ],
            ["id", "product_id", "product_uom_qty", "quantity_done"]
        )
        
        if not moves:
            resultado["errores"].append("No se encontraron movimientos de consumo")
            return resultado
        
        # Por cada move, analizar sus move.lines
        for move in moves:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [("move_id", "=", move["id"])],
                [
                    "id", "product_id", "lot_id", "package_id", 
                    "location_id", "location_dest_id", "qty_done"
                ]
            )
            
            for ml in move_lines:
                if ml["qty_done"] <= 0:
                    continue
                
                lote_consumido = ml["lot_id"][1] if ml.get("lot_id") else None
                paquete_consumido = ml["package_id"][1] if ml.get("package_id") else None
                location_dest_id = ml["location_dest_id"][0] if ml.get("location_dest_id") else None
                
                if not lote_consumido or not paquete_consumido:
                    resultado["errores"].append(
                        f"Línea {ml['id']} sin lote o paquete asignado, omitiendo"
                    )
                    continue
                
                # Obtener nombre de ubicación
                ubicacion_name = ml["location_dest_id"][1] if ml.get("location_dest_id") else "N/A"
                
                # Quitar sufijo -C del lote
                lote_original = lote_consumido.replace("-C", "")
                
                resultado["componentes"].append({
                    "producto": ml["product_id"][1] if ml.get("product_id") else "N/A",
                    "lote": lote_original,
                    "paquete": paquete_consumido,
                    "cantidad": ml["qty_done"],
                    "ubicacion": ubicacion_name
                })
        
        return resultado
    
    def _analizar_subproductos(self, mo_id: int) -> Dict:
        """
        Analiza subproductos a eliminar SIN modificarlos.
        Solo retorna información de lo que se haría.
        """
        resultado = {
            "subproductos": [],
            "errores": []
        }
        
        # Obtener producto principal
        mo = self.odoo.search_read(
            "mrp.production",
            [("id", "=", mo_id)],
            ["product_id"]
        )
        
        if not mo:
            resultado["errores"].append("Orden de fabricación no encontrada")
            return resultado
        
        main_product_id = mo[0]["product_id"][0]
        
        # Buscar subproductos (productos finished que no son el principal)
        finished_moves = self.odoo.search_read(
            "stock.move",
            [
                ("production_id", "=", mo_id),
                ("state", "=", "done"),
                ("product_id", "!=", main_product_id)
            ],
            ["id", "product_id", "product_uom_qty", "quantity_done", "location_dest_id"]
        )
        
        for move in finished_moves:
            ubicacion_name = move["location_dest_id"][1] if move.get("location_dest_id") else "N/A"
            
            resultado["subproductos"].append({
                "producto": move["product_id"][1] if move.get("product_id") else "N/A",
                "cantidad_actual": move["quantity_done"],
                "ubicacion": ubicacion_name
            })
        
        return resultado
    
    def _revertir_componentes(self, mo_id: int, odf_name: str) -> Dict:
        """
        Recupera componentes consumidos a sus paquetes originales.
        Busca stock.move de tipo consumo y crea transferencias internas.
        """
        resultado = {
            "componentes": [],
            "transferencias": [],
            "errores": []
        }
        
        # Buscar movimientos de consumo (moves con picking de tipo consumo/producción)
        moves = self.odoo.search_read(
            "stock.move",
            [
                ("raw_material_production_id", "=", mo_id),
                ("state", "=", "done")
            ],
            ["id", "product_id", "product_uom_qty", "quantity_done"]
        )
        
        if not moves:
            resultado["errores"].append("No se encontraron movimientos de consumo")
            return resultado
        
        # Por cada move, buscar sus move.lines (tienen info de paquetes y lotes)
        for move in moves:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [("move_id", "=", move["id"])],
                [
                    "id", "product_id", "lot_id", "package_id", 
                    "location_id", "location_dest_id", "qty_done"
                ]
            )
            
            for ml in move_lines:
                if ml["qty_done"] <= 0:
                    continue
                
                # Extraer info
                lote_consumido = ml["lot_id"][1] if ml.get("lot_id") else None
                paquete_consumido = ml["package_id"][1] if ml.get("package_id") else None
                location_actual_id = ml["location_dest_id"][0] if ml.get("location_dest_id") else None
                
                if not lote_consumido or not paquete_consumido:
                    resultado["errores"].append(
                        f"Línea {ml['id']} sin lote o paquete asignado, omitiendo"
                    )
                    continue
                
                # Quitar sufijo -C del lote si existe
                lote_original = lote_consumido.replace("-C", "")
                
                # Crear transferencia interna para reasignar al paquete
                try:
                    transferencia = self._crear_transferencia_recuperacion(
                        product_id=ml["product_id"][0],
                        lote_original=lote_original,
                        paquete_destino=paquete_consumido,
                        cantidad=ml["qty_done"],
                        location_id=location_actual_id,
                        odf_name=odf_name
                    )
                    
                    resultado["componentes"].append({
                        "producto": ml["product_id"][1] if ml.get("product_id") else "N/A",
                        "lote": lote_original,
                        "paquete": paquete_consumido,
                        "cantidad": ml["qty_done"],
                        "transferencia": transferencia
                    })
                    
                    resultado["transferencias"].append(transferencia)
                    
                except Exception as e:
                    resultado["errores"].append(
                        f"Error creando transferencia para {paquete_consumido}: {str(e)}"
                    )
        
        return resultado
    
    def _crear_transferencia_recuperacion(
        self, 
        product_id: int,
        lote_original: str,
        paquete_destino: str,
        cantidad: float,
        location_id: int,
        odf_name: str
    ) -> str:
        """
        Crea una transferencia interna para reasignar stock al paquete original.
        Origen y destino son la misma ubicación, solo cambia el paquete.
        """
        # Buscar el paquete por nombre
        packages = self.odoo.search_read(
            "stock.quant.package",
            [("name", "=", paquete_destino)],
            ["id"]
        )
        
        if not packages:
            raise ValueError(f"Paquete {paquete_destino} no encontrado")
        
        package_id = packages[0]["id"]
        
        # Buscar el lote
        lots = self.odoo.search_read(
            "stock.lot",
            [("name", "=", lote_original), ("product_id", "=", product_id)],
            ["id"]
        )
        
        if not lots:
            raise ValueError(f"Lote {lote_original} no encontrado para producto {product_id}")
        
        lot_id = lots[0]["id"]
        
        # Buscar picking type interno
        picking_types = self.odoo.search_read(
            "stock.picking.type",
            [("code", "=", "internal"), ("warehouse_id", "!=", False)],
            ["id"],
            limit=1
        )
        
        if not picking_types:
            raise ValueError("No se encontró picking type interno")
        
        picking_type_id = picking_types[0]["id"]
        
        # Crear picking
        picking_vals = {
            "picking_type_id": picking_type_id,
            "location_id": location_id,
            "location_dest_id": location_id,  # Misma ubicación
            "origin": f"Reversión {odf_name}: {paquete_destino}",
            "move_type": "direct"
        }
        
        picking_id = self.odoo.execute("stock.picking", "create", picking_vals)
        
        # Crear move
        move_vals = {
            "name": f"Recuperar {paquete_destino}",
            "picking_id": picking_id,
            "product_id": product_id,
            "product_uom_qty": cantidad,
            "product_uom": 1,  # Kg
            "location_id": location_id,
            "location_dest_id": location_id
        }
        
        move_id = self.odoo.execute("stock.move", "create", move_vals)
        
        # Confirmar y asignar
        self.odoo.execute("stock.picking", "action_confirm", [picking_id])
        self.odoo.execute("stock.picking", "action_assign", [picking_id])
        
        # Buscar move line creada y asignar paquete + qty_done
        move_lines = self.odoo.search_read(
            "stock.move.line",
            [("move_id", "=", move_id)],
            ["id"]
        )
        
        if move_lines:
            ml_id = move_lines[0]["id"]
            self.odoo.execute(
                "stock.move.line",
                "write",
                [ml_id],
                {
                    "result_package_id": package_id,
                    "lot_id": lot_id,
                    "qty_done": cantidad
                }
            )
        
        # Validar picking
        self.odoo.execute("stock.picking", "button_validate", [picking_id])
        
        # Obtener nombre del picking
        picking = self.odoo.search_read("stock.picking", [("id", "=", picking_id)], ["name"])
        picking_name = picking[0]["name"] if picking else f"ID:{picking_id}"
        
        return picking_name
    
    def _eliminar_subproductos(self, mo_id: int) -> Dict:
        """
        Pone en 0 los subproductos de la orden de fabricación.
        """
        resultado = {
            "subproductos": [],
            "errores": []
        }
        
        # Buscar movimientos de subproductos (finished_product_id = mo_id pero no es el producto principal)
        # En Odoo, los subproductos están en move_finished_ids pero con is_byproduct = True
        
        # Primero obtener el producto principal
        mo = self.odoo.search_read(
            "mrp.production",
            [("id", "=", mo_id)],
            ["product_id"]
        )
        
        if not mo:
            resultado["errores"].append("Orden de fabricación no encontrada")
            return resultado
        
        main_product_id = mo[0]["product_id"][0]
        
        # Buscar todos los moves finished
        finished_moves = self.odoo.search_read(
            "stock.move",
            [
                ("production_id", "=", mo_id),
                ("state", "=", "done"),
                ("product_id", "!=", main_product_id)  # Excluir producto principal
            ],
            ["id", "product_id", "product_uom_qty", "quantity_done"]
        )
        
        for move in finished_moves:
            try:
                # Actualizar cantidad a 0
                self.odoo.execute(
                    "stock.move",
                    "write",
                    [move["id"]],
                    {
                        "product_uom_qty": 0.0,
                        "quantity_done": 0.0
                    }
                )
                
                # También actualizar las move lines a 0
                move_lines = self.odoo.search_read(
                    "stock.move.line",
                    [("move_id", "=", move["id"])],
                    ["id"]
                )
                
                for ml in move_lines:
                    self.odoo.execute(
                        "stock.move.line",
                        "write",
                        [ml["id"]],
                        {"qty_done": 0.0}
                    )
                
                resultado["subproductos"].append({
                    "producto": move["product_id"][1] if move.get("product_id") else "N/A",
                    "cantidad_original": move["quantity_done"],
                    "nueva_cantidad": 0.0
                })
                
            except Exception as e:
                resultado["errores"].append(
                    f"Error eliminando subproducto {move['product_id'][1]}: {str(e)}"
                )
        
        return resultado
