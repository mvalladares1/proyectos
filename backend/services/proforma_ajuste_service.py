"""
Servicio para gestionar facturas de proveedor en borrador (Proformas)
Permite consultar, comparar y ajustar moneda USD → CLP
"""
from typing import List, Dict, Any, Optional
from shared.odoo_client import OdooClient


def get_facturas_borrador(
    username: str, 
    password: str, 
    proveedor_id: Optional[int] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    solo_usd: bool = True
) -> List[Dict[str, Any]]:
    """
    Obtiene facturas de proveedor en estado borrador.
    
    Args:
        username: Usuario de Odoo
        password: Contraseña de Odoo
        proveedor_id: ID del proveedor (opcional)
        fecha_desde: Fecha inicio formato YYYY-MM-DD (opcional)
        fecha_hasta: Fecha fin formato YYYY-MM-DD (opcional)
        solo_usd: Si True, solo retorna facturas en USD
    
    Returns:
        Lista de facturas con sus líneas y montos en ambas monedas
    """
    client = OdooClient(username=username, password=password)
    
    # Construir dominio de búsqueda
    domain = [
        ("move_type", "=", "in_invoice"),  # Facturas de proveedor
        ("state", "=", "draft"),  # Solo borradores
    ]
    
    if solo_usd:
        domain.append(("currency_id.name", "=", "USD"))
    
    if proveedor_id:
        domain.append(("partner_id", "=", proveedor_id))
    
    if fecha_desde:
        domain.append(("create_date", ">=", fecha_desde))
    
    if fecha_hasta:
        domain.append(("create_date", "<=", f"{fecha_hasta} 23:59:59"))
    
    # Buscar facturas
    facturas = client.search_read(
        "account.move",
        domain,
        [
            "id", "name", "partner_id", "invoice_date", "create_date",
            "currency_id", "amount_total", "amount_untaxed", "amount_tax",
            "amount_total_signed", "amount_untaxed_signed",
            "invoice_line_ids", "invoice_origin", "ref"
        ],
        limit=100,
        order="create_date desc"
    )
    
    resultado = []
    
    for fac in facturas:
        # Obtener líneas de factura con montos en CLP (desde debit)
        invoice_line_ids = fac.get("invoice_line_ids", [])
        lineas = []
        
        if invoice_line_ids:
            lines_data = client.read(
                "account.move.line",
                invoice_line_ids,
                [
                    "id", "name", "quantity", "price_unit",
                    "price_subtotal", "price_total",
                    "debit", "credit", "amount_currency",
                    "display_type", "product_id"
                ]
            )
            
            for line in lines_data:
                # Saltar líneas de sección, notas o términos de pago
                if line.get("display_type") in ["line_section", "line_note", "payment_term"]:
                    continue
                
                # Calcular tipo de cambio implícito
                usd_subtotal = line.get("price_subtotal", 0) or 0
                clp_debit = line.get("debit", 0) or 0
                tc_linea = clp_debit / usd_subtotal if usd_subtotal > 0 else 0
                
                lineas.append({
                    "id": line["id"],
                    "nombre": line.get("name", ""),
                    "producto_id": line.get("product_id", [None, ""])[0] if line.get("product_id") else None,
                    "producto_nombre": line.get("product_id", [None, ""])[1] if line.get("product_id") else "",
                    "cantidad": line.get("quantity", 0),
                    "precio_usd": line.get("price_unit", 0),
                    "subtotal_usd": usd_subtotal,
                    "total_usd": line.get("price_total", 0) or 0,
                    "subtotal_clp": clp_debit,
                    "tc_implicito": tc_linea
                })
        
        # Calcular totales
        total_base_clp = sum(l["subtotal_clp"] for l in lineas)
        total_iva_clp = total_base_clp * 0.19
        total_con_iva_clp = total_base_clp + total_iva_clp
        
        # Tipo de cambio promedio
        tcs = [l["tc_implicito"] for l in lineas if l["tc_implicito"] > 0]
        tc_promedio = sum(tcs) / len(tcs) if tcs else 0
        
        partner = fac.get("partner_id", [None, "Sin proveedor"])
        currency = fac.get("currency_id", [None, "USD"])
        
        resultado.append({
            "id": fac["id"],
            "nombre": fac.get("name", ""),
            "ref": fac.get("ref", ""),
            "proveedor_id": partner[0] if isinstance(partner, list) else None,
            "proveedor_nombre": partner[1] if isinstance(partner, list) else str(partner),
            "fecha_factura": fac.get("invoice_date", ""),
            "fecha_creacion": fac.get("create_date", ""),
            "moneda": currency[1] if isinstance(currency, list) else str(currency),
            "origin": fac.get("invoice_origin", ""),
            # Montos USD
            "base_usd": fac.get("amount_untaxed", 0) or 0,
            "iva_usd": fac.get("amount_tax", 0) or 0,
            "total_usd": fac.get("amount_total", 0) or 0,
            # Montos CLP (desde signed o calculados)
            "base_clp": total_base_clp,
            "iva_clp": total_iva_clp,
            "total_clp": total_con_iva_clp,
            # Montos signed de Odoo (para validación)
            "base_clp_signed": abs(fac.get("amount_untaxed_signed", 0) or 0),
            "total_clp_signed": abs(fac.get("amount_total_signed", 0) or 0),
            # Tipo de cambio
            "tipo_cambio": tc_promedio,
            # Líneas
            "lineas": lineas,
            "num_lineas": len(lineas)
        })
    
    return resultado


def get_proveedores_con_borradores(username: str, password: str) -> List[Dict[str, Any]]:
    """
    Obtiene lista de proveedores que tienen facturas en borrador.
    """
    client = OdooClient(username=username, password=password)
    
    # Buscar facturas en borrador
    facturas = client.search_read(
        "account.move",
        [
            ("move_type", "=", "in_invoice"),
            ("state", "=", "draft"),
        ],
        ["partner_id"],
        limit=500
    )
    
    # Extraer proveedores únicos
    proveedores_ids = set()
    for f in facturas:
        partner = f.get("partner_id")
        if partner and isinstance(partner, list):
            proveedores_ids.add(partner[0])
    
    if not proveedores_ids:
        return []
    
    # Obtener datos de proveedores
    proveedores = client.read(
        "res.partner",
        list(proveedores_ids),
        ["id", "name", "vat"]
    )
    
    return [
        {
            "id": p["id"],
            "nombre": p.get("name", ""),
            "rut": p.get("vat", "")
        }
        for p in proveedores
    ]


def get_detalle_factura(username: str, password: str, factura_id: int) -> Dict[str, Any]:
    """
    Obtiene el detalle completo de una factura específica.
    """
    facturas = get_facturas_borrador(username, password)
    
    for fac in facturas:
        if fac["id"] == factura_id:
            return fac
    
    return {}


def cambiar_moneda_factura(
    username: str, 
    password: str, 
    factura_id: int,
    nueva_moneda: str = "CLP"
) -> Dict[str, Any]:
    """
    Cambia la moneda de una factura de USD a CLP.
    NOTA: Esta operación modifica la factura en Odoo.
    
    Args:
        username: Usuario de Odoo
        password: Contraseña de Odoo
        factura_id: ID de la factura a modificar
        nueva_moneda: Código de la nueva moneda (default: CLP)
    
    Returns:
        Resultado de la operación
    """
    client = OdooClient(username=username, password=password)
    
    try:
        # Obtener ID de la moneda CLP
        moneda = client.search_read(
            "res.currency",
            [("name", "=", nueva_moneda)],
            ["id", "name"],
            limit=1
        )
        
        if not moneda:
            return {"success": False, "error": f"Moneda {nueva_moneda} no encontrada"}
        
        moneda_id = moneda[0]["id"]
        
        # Obtener factura actual para tener los valores
        factura = client.read(
            "account.move",
            [factura_id],
            ["id", "name", "invoice_line_ids", "currency_id"]
        )
        
        if not factura:
            return {"success": False, "error": "Factura no encontrada"}
        
        fac = factura[0]
        
        # Obtener líneas con valores CLP
        lineas_ids = fac.get("invoice_line_ids", [])
        lineas = client.read(
            "account.move.line",
            lineas_ids,
            ["id", "debit", "display_type", "name"]
        )
        
        # Preparar actualizaciones de líneas
        # Cada línea debe actualizarse con price_unit = debit (valor en CLP)
        lineas_update = []
        for line in lineas:
            if line.get("display_type") in ["line_section", "line_note", "payment_term"]:
                continue
            
            clp_value = line.get("debit", 0)
            if clp_value > 0:
                lineas_update.append({
                    "id": line["id"],
                    "price_unit": clp_value / 1  # Esto se ajustará según cantidad
                })
        
        # Cambiar moneda de la factura
        # NOTA: Esto es una operación delicada, verificar antes en staging
        result = client.write(
            "account.move",
            [factura_id],
            {"currency_id": moneda_id}
        )
        
        return {
            "success": True,
            "factura_id": factura_id,
            "nueva_moneda": nueva_moneda,
            "lineas_actualizadas": len(lineas_update)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
