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
                
                # VERIFICAR si el paquete ya tiene estos kg asignados
                paquete_necesita_transfer = self._verificar_si_necesita_transferencia(
                    paquete_consumido,
                    ml["product_id"][0],
                    lote_original,
                    ml["qty_done"]
                )
                
                # Solo incluir componentes que necesitan transferencia (filtrar ya revertidos)
                if paquete_necesita_transfer:
                    resultado["componentes"].append({
                        "producto": ml["product_id"][1] if ml.get("product_id") else "N/A",
                        "lote": lote_original,
                        "paquete": paquete_consumido,
                        "cantidad": ml["qty_done"],
                        "ubicacion": ubicacion_name
                    })
        
        return resultado
    
    def _verificar_si_necesita_transferencia(
        self, 
        paquete_nombre: str, 
        producto_id: int, 
        lote_nombre: str, 
        cantidad_esperada: float
    ) -> bool:
        """
        Verifica si un paquete necesita transferencia o ya tiene el stock asignado.
        Retorna True si necesita transferencia, False si ya tiene el stock.
        """
        # Buscar el paquete
        packages = self.odoo.search_read(
            "stock.quant.package",
            [("name", "=", paquete_nombre)],
            ["id"]
        )
        
        if not packages:
            return True  # Paquete no existe, necesita crearse
        
        package_id = packages[0]["id"]
        
        # Buscar quants del paquete con ese producto y lote
        quants = self.odoo.search_read(
            "stock.quant",
            [
                ("package_id", "=", package_id),
                ("product_id", "=", producto_id),
                ("lot_id.name", "=", lote_nombre),
                ("quantity", ">", 0)
            ],
            ["quantity"]
        )
        if not quants:
            return True  # No tiene stock de ese producto/lote, necesita transferencia
        
        # Si tiene stock, verificar que sea la cantidad correcta
        cantidad_actual = sum(q["quantity"] for q in quants)
        
        # Si ya tiene la cantidad esperada (con margen de 0.01), no necesita transferencia
        if abs(cantidad_actual - cantidad_esperada) < 0.01:
            return False
        
        return True  # Tiene stock pero no la cantidad correcta
    
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
        
        # Por cada move, obtener sus move_lines (cada línea tiene un paquete diferente)
        for move in finished_moves:
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [("move_id", "=", move["id"])],
                ["id", "qty_done", "result_package_id", "lot_id", "location_dest_id"]
            )
            
            for ml in move_lines:
                if ml["qty_done"] <= 0:
                    continue
                
                paquete_name = ml["result_package_id"][1] if ml.get("result_package_id") else "Sin paquete"
                lote_name = ml["lot_id"][1] if ml.get("lot_id") else "Sin lote"
                ubicacion_name = ml["location_dest_id"][1] if ml.get("location_dest_id") else "N/A"
                
                resultado["subproductos"].append({
                    "producto": move["product_id"][1] if move.get("product_id") else "N/A",
                    "paquete": paquete_name,
                    "lote": lote_name,
                    "cantidad_actual": ml["qty_done"],
                    "ubicacion": ubicacion_name,
                    "move_line_id": ml["id"]  # Importante para poder actualizarlo después
                })
        
        return resultado
    
    def _revertir_componentes(self, mo_id: int, odf_name: str) -> Dict:
        """
        Recupera componentes consumidos a sus paquetes originales.
        Crea UNA SOLA transferencia con múltiples líneas (moves).
        """
        resultado = {
            "componentes": [],
            "transferencias": [],
            "errores": []
        }
        
        # Recolectar todos los componentes que necesitan transferencia
        componentes_a_transferir = []
        
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
        
        # Por cada move, buscar sus move.lines
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
                location_id = ml["location_dest_id"][0] if ml.get("location_dest_id") else None
                
                if not lote_consumido or not paquete_consumido:
                    resultado["errores"].append(
                        f"Línea {ml['id']} sin lote o paquete asignado, omitiendo"
                    )
                    continue
                
                lote_original = lote_consumido.replace("-C", "")
                
                # VERIFICAR si necesita transferencia
                if not self._verificar_si_necesita_transferencia(
                    paquete_consumido,
                    ml["product_id"][0],
                    lote_original,
                    ml["qty_done"]
                ):
                    resultado["errores"].append(
                        f"⚠️ Paquete {paquete_consumido} ya tiene {ml['qty_done']} kg asignados, omitiendo"
                    )
                    continue
                
                # Agregar a la lista de componentes a transferir
                componentes_a_transferir.append({
                    "product_id": ml["product_id"][0],
                    "producto_nombre": ml["product_id"][1] if ml.get("product_id") else "N/A",
                    "lote_original": lote_original,
                    "paquete": paquete_consumido,
                    "cantidad": ml["qty_done"],
                    "location_id": location_id
                })
        
        # Si no hay componentes a transferir, retornar
        if not componentes_a_transferir:
            resultado["errores"].append("No hay componentes que necesiten transferencia")
            return resultado
        
        # Crear UNA SOLA transferencia con todos los componentes
        try:
            transfer_info = self._crear_transferencia_unica(
                componentes_a_transferir,
                odf_name
            )
            
            # Agregar info de cada componente
            for comp in componentes_a_transferir:
                resultado["componentes"].append({
                    "producto": comp["producto_nombre"],
                    "lote": comp["lote_original"],
                    "paquete": comp["paquete"],
                    "cantidad": comp["cantidad"],
                    "transferencia": transfer_info["name"]
                })
            
            # Agregar info de la transferencia única
            resultado["transferencias"].append({
                "id": transfer_info["id"],
                "nombre": transfer_info["name"],
                "total_lineas": len(componentes_a_transferir)
            })
            
        except Exception as e:
            resultado["errores"].append(f"Error creando transferencia: {str(e)}")
        
        return resultado
    
    def _crear_transferencia_unica(self, componentes: list, odf_name: str) -> Dict:
        """
        Crea UNA transferencia interna con múltiples moves/lines para todos los componentes.
        
        Args:
            componentes: Lista de dicts con keys: product_id, lote_original, paquete, cantidad, location_id
            odf_name: Nombre de la ODF para referencia
        
        Returns:
            Dict con id y name de la transferencia creada
        """
        if not componentes:
            raise ValueError("No hay componentes para transferir")
        
        # Usar la ubicación del primer componente (normalmente todas son la misma)
        location_id = componentes[0]["location_id"]
        
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
            "location_dest_id": location_id,
            "origin": f"Reversión {odf_name} ({len(componentes)} componentes)",
            "move_type": "direct"
        }
        
        picking_id = self.odoo.execute("stock.picking", "create", picking_vals)
        
        # Buscar UoM "kg" directamente
        uom_kg = self.odoo.search_read(
            "uom.uom",
            [("name", "=", "kg")],
            ["id"],
            limit=1
        )
        
        if not uom_kg:
            raise ValueError("UoM 'kg' no encontrada en el sistema")
        
        uom_kg_id = uom_kg[0]["id"]
        
        # Crear un move por cada componente
        for comp in componentes:
            move_vals = {
                "name": f"Recuperar {comp['paquete']}",
                "picking_id": picking_id,
                "product_id": comp["product_id"],
                "product_uom_qty": comp["cantidad"],
                "product_uom": uom_kg_id,
                "location_id": location_id,
                "location_dest_id": location_id
            }
            
            move_id = self.odoo.execute("stock.move", "create", move_vals)
            comp["move_id"] = move_id  # Guardar para después
        
        # Confirmar y asignar picking
        self.odoo.execute("stock.picking", "action_confirm", [picking_id])
        self.odoo.execute("stock.picking", "action_assign", [picking_id])
        
        # Configurar cada move_line con su paquete y lote
        for comp in componentes:
            # Buscar el paquete
            packages = self.odoo.search_read(
                "stock.quant.package",
                [("name", "=", comp["paquete"])],
                ["id"]
            )
            
            if not packages:
                raise ValueError(f"Paquete {comp['paquete']} no encontrado")
            
            package_id = packages[0]["id"]
            
            # Buscar el lote
            lots = self.odoo.search_read(
                "stock.lot",
                [("name", "=", comp["lote_original"]), ("product_id", "=", comp["product_id"])],
                ["id"]
            )
            
            if not lots:
                raise ValueError(f"Lote {comp['lote_original']} no encontrado")
            
            lot_id = lots[0]["id"]
            
            # Buscar la move line del move
            move_lines = self.odoo.search_read(
                "stock.move.line",
                [("move_id", "=", comp["move_id"])],
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
                        "qty_done": comp["cantidad"]
                    }
                )
        
        # NO VALIDAR - dejar en BORRADOR
        
        # Obtener nombre del picking
        picking = self.odoo.search_read("stock.picking", [("id", "=", picking_id)], ["name"])
        picking_name = picking[0]["name"] if picking else f"ID:{picking_id}"
        
        return {"id": picking_id, "name": picking_name}
    
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
        
        # Buscar UoM "kg" directamente
        uom_kg = self.odoo.search_read(
            "uom.uom",
            [("name", "=", "kg")],
            ["id"],
            limit=1
        )
        
        if not uom_kg:
            raise ValueError("UoM 'kg' no encontrada en el sistema")
        
        uom_kg_id = uom_kg[0]["id"]
        
        # Crear move
        move_vals = {
            "name": f"Recuperar {paquete_destino}",
            "picking_id": picking_id,
            "product_id": product_id,
            "product_uom_qty": cantidad,
            "product_uom": uom_kg_id,
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
        
        # NO validar - dejar en BORRADOR para revisión manual
        # self.odoo.execute("stock.picking", "button_validate", [picking_id])
        
        # Obtener nombre del picking
        picking = self.odoo.search_read("stock.picking", [("id", "=", picking_id)], ["name"])
        picking_name = picking[0]["name"] if picking else f"ID:{picking_id}"
        
        return {"id": picking_id, "name": picking_name}
    
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
