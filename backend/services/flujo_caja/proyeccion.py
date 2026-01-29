"""
Módulo de proyección de flujo de caja.
Calcula flujos proyectados basados en documentos pendientes.
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


class ProyeccionFlujo:
    """Calcula proyecciones de flujo de caja basadas en documentos."""
    
    def __init__(self, odoo_client, clasificar_cuenta_fn, estructura_flujo: Dict):
        """
        Args:
            odoo_client: Instancia de OdooClient
            clasificar_cuenta_fn: Función para clasificar cuentas
            estructura_flujo: Estructura de flujo por categoría
        """
        self.odoo = odoo_client
        self.clasificar_cuenta = clasificar_cuenta_fn
        self.estructura_flujo = estructura_flujo
    
    def calcular_proyeccion(self, fecha_inicio: str, fecha_fin: str,
                           company_id: int = None) -> Dict:
        """
        Calcula el flujo proyectado basado en documentos pendientes.
        
        Args:
            fecha_inicio: Fecha inicio YYYY-MM-DD
            fecha_fin: Fecha fin YYYY-MM-DD
            company_id: ID de compañía
            
        Returns:
            Proyección estructurada por actividad
        """
        proyeccion = {
            "actividades": {},
            "total_ingresos": 0.0,
            "total_egresos": 0.0
        }
        
        # Inicializar estructura
        detalles_por_concepto = {}
        montos_por_concepto = {}
        
        for k, v in self.estructura_flujo.items():
            for linea in v.get("lineas", []):
                codigo = linea.get("codigo")
                if codigo:
                    detalles_por_concepto[codigo] = []
                    montos_por_concepto[codigo] = 0.0
        
        # Buscar documentos
        moves = self._obtener_documentos(fecha_inicio, fecha_fin, company_id)
        
        if not moves:
            return proyeccion
        
        # Obtener líneas
        move_ids = [m['id'] for m in moves]
        lines_by_move, cuentas_info = self._obtener_lineas_y_cuentas(move_ids)
        
        # Contadores para warnings
        docs_sin_etiqueta = []
        
        # Procesar documentos
        for move in moves:
            result = self._procesar_documento(
                move, lines_by_move, cuentas_info, 
                fecha_inicio, fecha_fin,
                montos_por_concepto, detalles_por_concepto,
                docs_sin_etiqueta
            )
        
        # Construir resultado
        proyeccion = self._construir_resultado(
            montos_por_concepto, 
            detalles_por_concepto,
            docs_sin_etiqueta
        )
        
        return proyeccion
    
    def _obtener_documentos(self, fecha_inicio: str, fecha_fin: str,
                           company_id: int = None) -> List[Dict]:
        """Obtiene documentos para proyección."""
        domain_base = [
            ('move_type', 'in', ['out_invoice', 'in_invoice']),
            ('state', '!=', 'cancel'),
            '|', ('state', '=', 'draft'), 
            '&', ('state', '=', 'posted'), ('payment_state', '!=', 'paid')
        ]
        
        if company_id:
            domain_base.append(('company_id', '=', company_id))
        
        # Filtro por fechas (cualquiera de las 3)
        domain = domain_base + [
            '|', '|',
            '&', ('x_studio_fecha_de_pago', '>=', fecha_inicio), ('x_studio_fecha_de_pago', '<=', fecha_fin),
            '&', ('invoice_date_due', '>=', fecha_inicio), ('invoice_date_due', '<=', fecha_fin),
            '&', ('invoice_date', '>=', fecha_inicio), ('invoice_date', '<=', fecha_fin)
        ]
        
        campos = ['id', 'name', 'ref', 'partner_id', 'invoice_date', 'invoice_date_due',
                 'amount_total', 'amount_residual', 'move_type', 'state', 'payment_state',
                 'date', 'x_studio_fecha_de_pago']
        
        try:
            moves = self.odoo.search_read('account.move', domain, campos, limit=2000)
            return moves or []
        except Exception as e:
            # Fallback sin campo custom
            if "x_studio_fecha_de_pago" in str(e):
                campos.remove('x_studio_fecha_de_pago')
                try:
                    return self.odoo.search_read('account.move', domain_base, campos, limit=2000) or []
                except:
                    return []
            return []
    
    def _obtener_lineas_y_cuentas(self, move_ids: List[int]) -> Tuple[Dict, Dict]:
        """Obtiene líneas de facturas y info de cuentas."""
        domain_lines = [
            ('move_id', 'in', move_ids),
            ('display_type', 'not in', ['line_section', 'line_note'])
        ]
        
        try:
            lines = self.odoo.search_read(
                'account.move.line', domain_lines,
                ['move_id', 'account_id', 'price_subtotal', 'name'],
                limit=10000
            )
        except:
            lines = []
        
        # Agrupar por move_id
        lines_by_move = {}
        for l in lines:
            mid = l['move_id'][0] if isinstance(l.get('move_id'), (list, tuple)) else l.get('move_id')
            lines_by_move.setdefault(mid, []).append(l)
        
        # Info de cuentas
        account_ids = list(set(
            l['account_id'][0] if isinstance(l.get('account_id'), (list, tuple)) else l.get('account_id')
            for l in lines if l.get('account_id')
        ))
        
        cuentas_info = {}
        if account_ids:
            try:
                acc_read = self.odoo.read('account.account', account_ids, ['code', 'name'])
                cuentas_info = {a['id']: a for a in acc_read}
            except:
                pass
        
        return lines_by_move, cuentas_info
    
    def _procesar_documento(self, move: Dict, lines_by_move: Dict, cuentas_info: Dict,
                           fecha_inicio: str, fecha_fin: str,
                           montos_por_concepto: Dict, detalles_por_concepto: Dict,
                           docs_sin_etiqueta: List) -> None:
        """Procesa un documento individual."""
        move_id = move['id']
        monto_documento = move.get('amount_residual', 0) if move.get('state') == 'posted' else move.get('amount_total', 0)
        
        if monto_documento == 0:
            return
        
        # Determinar fecha de proyección
        fecha_proyeccion, es_estimada = self._determinar_fecha_proyeccion(move)
        
        if not fecha_proyeccion or not (fecha_inicio <= fecha_proyeccion <= fecha_fin):
            return
        
        # Signo del flujo
        es_ingreso = move['move_type'] == 'out_invoice'
        signo_flujo = 1 if es_ingreso else -1
        monto_flujo = monto_documento * signo_flujo
        
        # Líneas base
        base_lines = lines_by_move.get(move_id, [])
        total_base = sum(l.get('price_subtotal', 0) for l in base_lines)
        
        if not base_lines or total_base == 0:
            return
        
        partner_name = move['partner_id'][1] if isinstance(move.get('partner_id'), (list, tuple)) else (move.get('partner_id') or "Varios")
        
        for line in base_lines:
            subtotal = line.get('price_subtotal', 0)
            if subtotal == 0:
                continue
            
            peso = subtotal / total_base
            monto_parte = monto_flujo * peso
            
            # Obtener cuenta contable (necesaria para in_invoice y para detalle)
            acc_id = line['account_id'][0] if isinstance(line.get('account_id'), (list, tuple)) else line.get('account_id')
            acc_code = cuentas_info.get(acc_id, {}).get('code', '')
            
            # Clasificar según tipo de documento
            # Facturas de cliente (out_invoice) -> 1.1.1 Cobros procedentes de ventas
            # Facturas de proveedor (in_invoice) -> clasificación por cuenta
            if es_ingreso:
                # Facturas de cliente van directo a concepto 1.1.1
                categoria = "1.1.1"
            else:
                # Facturas de proveedor: usar clasificación por cuenta contable
                categoria, _ = self.clasificar_cuenta(acc_code)
                if not categoria:
                    categoria = "UNCLASSIFIED"
            
            montos_por_concepto[categoria] = montos_por_concepto.get(categoria, 0) + monto_parte
            
            # Etiqueta
            etiquetas_nombres = [line.get('name', '')] if line.get('name') else []
            sin_etiqueta = not line.get('name')
            
            entry = {
                "id": move_id,
                "documento": move.get('name') or move.get('ref') or str(move_id),
                "partner": partner_name,
                "fecha_emision": move.get('invoice_date'),
                "fecha_venc": fecha_proyeccion,
                "es_estimada": es_estimada,
                "estado": "Borrador" if move.get('state') == 'draft' else "Abierto",
                "monto": round(monto_parte, 0),
                "cuenta": acc_code,
                "cuenta_nombre": cuentas_info.get(acc_id, {}).get('name', ''),
                "tipo": "Factura Cliente" if es_ingreso else "Factura Proveedor",
                "linea_nombre": line.get('name', ''),
                "etiquetas": etiquetas_nombres,
                "sin_etiqueta": sin_etiqueta
            }
            
            if sin_etiqueta and move_id not in [d['id'] for d in docs_sin_etiqueta]:
                docs_sin_etiqueta.append({
                    "id": move_id,
                    "documento": entry["documento"],
                    "partner": partner_name,
                    "monto": round(monto_flujo, 0)
                })
            
            if categoria not in detalles_por_concepto:
                detalles_por_concepto[categoria] = []
            detalles_por_concepto[categoria].append(entry)
    
    def _determinar_fecha_proyeccion(self, move: Dict) -> Tuple[Optional[str], bool]:
        """
        Determina la fecha de proyección de un documento.
        
        Returns:
            Tuple (fecha, es_estimada)
        """
        fecha_pago_acordada = move.get('x_studio_fecha_de_pago')
        fecha_vencimiento = move.get('invoice_date_due')
        fecha_factura = move.get('invoice_date') or move.get('date')
        
        if fecha_pago_acordada:
            return fecha_pago_acordada, False
        elif fecha_vencimiento:
            return fecha_vencimiento, False
        elif move.get('state') == 'draft' and fecha_factura:
            try:
                dt_factura = datetime.strptime(fecha_factura, '%Y-%m-%d')
                dt_estimada = dt_factura + timedelta(days=30)
                return dt_estimada.strftime('%Y-%m-%d'), True
            except:
                pass
        
        return fecha_factura, False if fecha_factura else (None, False)
    
    def _construir_resultado(self, montos_por_concepto: Dict, 
                            detalles_por_concepto: Dict,
                            docs_sin_etiqueta: List) -> Dict:
        """Construye resultado final de proyección."""
        proyeccion = {
            "actividades": {},
            "sin_clasificar": [],
            "monto_sin_clasificar": 0
        }
        
        if "UNCLASSIFIED" in detalles_por_concepto:
            proyeccion["sin_clasificar"] = detalles_por_concepto["UNCLASSIFIED"]
            proyeccion["monto_sin_clasificar"] = montos_por_concepto.get("UNCLASSIFIED", 0)
        
        for cat_key, cat_data in self.estructura_flujo.items():
            conceptos_res = []
            subtotal_actividad = 0.0
            
            for linea in cat_data.get("lineas", []):
                codigo = linea.get("codigo")
                if not codigo:
                    continue
                    
                monto = montos_por_concepto.get(codigo, 0)
                docs = detalles_por_concepto.get(codigo, [])
                
                docs.sort(key=lambda x: x.get('fecha_venc') or '9999-12-31')
                
                if monto != 0 or docs:
                    conceptos_res.append({
                        "codigo": codigo,
                        "nombre": linea.get("nombre", ""),
                        "monto": round(monto, 0),
                        "documentos": docs
                    })
                    subtotal_actividad += monto
            
            proyeccion["actividades"][cat_key] = {
                "nombre": cat_data.get("nombre", ""),
                "subtotal": round(subtotal_actividad, 0),
                "subtotal_nombre": cat_data.get("subtotal_nombre", "Subtotal"),
                "conceptos": conceptos_res
            }
        
        # Warnings
        if docs_sin_etiqueta:
            proyeccion["warnings"] = [{
                "tipo": "SIN_ETIQUETAS",
                "mensaje": f"{len(docs_sin_etiqueta)} documento(s) no tienen etiquetas definidas",
                "documentos": docs_sin_etiqueta[:20]
            }]
        
        return proyeccion
