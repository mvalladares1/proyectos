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
        
        # Obtener email del proveedor
        proveedor_email = ""
        partner_id = partner[0] if isinstance(partner, list) else None
        if partner_id:
            try:
                partner_data = client.read("res.partner", [partner_id], ["email"])
                if partner_data:
                    proveedor_email = partner_data[0].get("email", "") or ""
            except:
                pass
        
        resultado.append({
            "id": fac["id"],
            "nombre": fac.get("name", ""),
            "ref": fac.get("ref", ""),
            "proveedor_id": partner[0] if isinstance(partner, list) else None,
            "proveedor_nombre": partner[1] if isinstance(partner, list) else str(partner),
            "proveedor_email": proveedor_email,
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
    # Obtener datos de la factura primero
    facturas = get_facturas_borrador(username, password)
    factura = None
    for f in facturas:
        if f["id"] == factura_id:
            factura = f
            break
    
    if not factura:
        return {"success": False, "error": "Factura no encontrada"}
    
    return aplicar_conversion_clp(username, password, factura_id, factura.get("lineas", []))


def aplicar_conversion_clp(
    username: str,
    password: str,
    factura_id: int,
    lineas: List[Dict]
) -> Dict[str, Any]:
    """
    Aplica la conversión USD → CLP actualizando:
    1. La moneda de la factura a CLP
    2. Los precios unitarios de cada línea al valor CLP
    
    Args:
        username: Usuario Odoo
        password: Contraseña Odoo
        factura_id: ID de la factura
        lineas: Lista de líneas con subtotal_clp y cantidad
    
    Returns:
        Resultado de la operación
    """
    client = OdooClient(username=username, password=password)
    
    try:
        # 1. Obtener ID de moneda CLP
        moneda_clp = client.search_read(
            "res.currency",
            [("name", "=", "CLP")],
            ["id"],
            limit=1
        )
        
        if not moneda_clp:
            return {"success": False, "error": "Moneda CLP no encontrada en Odoo"}
        
        clp_id = moneda_clp[0]["id"]
        
        # 2. Verificar que la factura está en borrador
        factura = client.read(
            "account.move",
            [factura_id],
            ["id", "name", "state", "move_type"]
        )
        
        if not factura:
            return {"success": False, "error": "Factura no encontrada"}
        
        if factura[0].get("state") != "draft":
            return {"success": False, "error": "Solo se pueden modificar facturas en estado borrador"}
        
        # 3. Actualizar precio unitario de cada línea
        lineas_actualizadas = 0
        errores_lineas = []
        
        for linea in lineas:
            try:
                linea_id = linea.get("id")
                cantidad = linea.get("cantidad", 1)
                subtotal_clp = linea.get("subtotal_clp", 0)
                
                if not linea_id or cantidad == 0:
                    continue
                
                # Calcular precio unitario en CLP
                precio_unit_clp = subtotal_clp / cantidad if cantidad else 0
                
                # Actualizar la línea
                client.write(
                    "account.move.line",
                    [linea_id],
                    {"price_unit": precio_unit_clp}
                )
                lineas_actualizadas += 1
                
            except Exception as e:
                errores_lineas.append(f"Línea {linea_id}: {str(e)}")
        
        # 4. Cambiar la moneda de la factura
        client.write(
            "account.move",
            [factura_id],
            {"currency_id": clp_id}
        )
        
        return {
            "success": True,
            "factura_id": factura_id,
            "lineas_actualizadas": lineas_actualizadas,
            "errores_lineas": errores_lineas if errores_lineas else None
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}


def enviar_proforma_email(
    username: str,
    password: str,
    factura_id: int,
    email_destino: str,
    pdf_bytes: bytes,
    nombre_factura: str,
    proveedor_nombre: str
) -> Dict[str, Any]:
    """
    Envía una proforma por correo electrónico usando Odoo mail.
    
    Args:
        username: Usuario Odoo
        password: Contraseña Odoo
        factura_id: ID de la factura
        email_destino: Email del destinatario
        pdf_bytes: Contenido del PDF en bytes
        nombre_factura: Nombre de la factura para el asunto
        proveedor_nombre: Nombre del proveedor
    
    Returns:
        Resultado de la operación
    """
    import base64
    
    client = OdooClient(username=username, password=password)
    
    try:
        # Codificar PDF en base64
        pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
        
        # Crear adjunto vinculado a la factura (quedará en Odoo)
        attachment_id = client.execute(
            "ir.attachment",
            "create",
            [{
                "name": f"Proforma_{nombre_factura}.pdf",
                "type": "binary",
                "datas": pdf_base64,
                "res_model": "account.move",
                "res_id": factura_id,
                "mimetype": "application/pdf",
                "description": f"Proforma enviada por correo"
            }]
        )
        
        if not attachment_id:
            raise Exception("No se pudo crear el adjunto en Odoo")
        
        # Crear y enviar correo
        asunto = f"Proforma {nombre_factura} - Rio Futuro"
        
        cuerpo_html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2E7D32;">Proforma de Proveedor</h2>
            <p>Estimado(a) <strong>{proveedor_nombre}</strong>,</p>
            <p>Adjunto encontrará la proforma correspondiente a la factura <strong>{nombre_factura}</strong>.</p>
            <br>
            <p>Detalle:</p>
            <ul>
                <li><strong>Factura:</strong> {nombre_factura}</li>
                <li><strong>Moneda:</strong> CLP (Pesos Chilenos)</li>
            </ul>
            <br>
            <p>Por favor revise el documento adjunto y no dude en contactarnos si tiene alguna consulta.</p>
            <br>
            <p>Saludos cordiales,</p>
            <p><strong>Rio Futuro Procesos</strong></p>
            <hr style="border: 1px solid #ddd; margin-top: 20px;">
            <p style="font-size: 11px; color: #888;">
                Este correo fue enviado automáticamente desde el sistema de gestión de Rio Futuro.
            </p>
        </div>
        """
        
        # Crear mensaje de correo usando el servidor configurado en Odoo
        mail_id = client.execute(
            "mail.mail",
            "create",
            [{
                "subject": asunto,
                "body_html": cuerpo_html,
                "email_to": email_destino,
                "email_from": "notificaciones-rfp@riofuturo.cl",  # Servidor configurado en Odoo
                "attachment_ids": [(6, 0, [int(attachment_id)])],  # Tupla para many2many
                "auto_delete": True
            }]
        )
        
        if not mail_id:
            raise Exception("No se pudo crear el correo en Odoo")
        
        # Enviar el correo
        client.execute("mail.mail", "send", [mail_id])
        
        # Registrar el mensaje en el chatter de la factura para historial
        mensaje_chatter = f"""
        <p>📧 <strong>Proforma enviada por correo electrónico</strong></p>
        <ul>
            <li><strong>Destinatario:</strong> {email_destino}</li>
            <li><strong>Asunto:</strong> {asunto}</li>
            <li><strong>Archivo adjunto:</strong> Proforma_{nombre_factura}.pdf</li>
        </ul>
        <p><em>Enviado automáticamente desde el Dashboard de Recepciones</em></p>
        """
        
        client.execute(
            "account.move",
            "message_post",
            [factura_id],
            {
                "body": mensaje_chatter,
                "message_type": "comment",
                "subtype_xmlid": "mail.mt_note",
                "attachment_ids": [(6, 0, [int(attachment_id)])]  # Tupla para many2many
            }
        )
        
        return {
            "success": True,
            "mail_id": mail_id,
            "attachment_id": attachment_id,
            "email_destino": email_destino,
            "factura": nombre_factura
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
