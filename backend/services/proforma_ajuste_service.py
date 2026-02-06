"""
Servicio para gestionar facturas de proveedor en borrador (Proformas)
Permite consultar, comparar y ajustar moneda USD → CLP
"""
from typing import List, Dict, Any, Optional
from shared.odoo_client import OdooClient

# Categorías que SÍ son productos de fruta (incluir solo estas)
CATEGORIAS_PRODUCTOS = ["PRODUCTOS", "FRUTA", "PRODUCTO"]

# Keywords de productos que indican que es fruta
KEYWORDS_FRUTA = [
    "ARANDANO", "ARÁNDANO", "BLUEBERRY",
    "FRAMBUESA", "RASPBERRY", 
    "FRUTILLA", "STRAWBERRY",
    "MORA", "BLACKBERRY",
    "CEREZA", "CHERRY",
    "AR ", " AR", "AR-", "AR_",
    "FB ", " FB", "FB-", "FB_",
    "FR ", " FR", "FR-", "FR_",
    "MO ", " MO", "MO-", "MO_",
    "CE ", " CE", "CE-", "CE_",
    "IQF", "BLOCK"
]


def tiene_productos_fruta(client: OdooClient, invoice_line_ids: List[int]) -> bool:
    """
    Verifica si una factura contiene productos de fruta.
    Usa la misma lógica que recepciones para detectar fruta.
    
    Args:
        client: Cliente Odoo
        invoice_line_ids: IDs de líneas de factura
        
    Returns:
        True si tiene al menos un producto de fruta
    """
    if not invoice_line_ids:
        return False
    
    try:
        # Leer líneas con información del producto
        lines_data = client.read(
            "account.move.line",
            invoice_line_ids,
            ["product_id", "display_type", "name"]
        )
        
        # Obtener IDs de productos únicos (excluir líneas de sección/notas)
        product_ids = []
        for line in lines_data:
            if line.get("display_type") in ["line_section", "line_note", "payment_term"]:
                continue
            if line.get("product_id"):
                prod_id = line["product_id"][0] if isinstance(line["product_id"], list) else line["product_id"]
                if prod_id and prod_id not in product_ids:
                    product_ids.append(prod_id)
        
        if not product_ids:
            return False
        
        # Leer productos con su categoría y nombre
        products = client.read(
            "product.product",
            product_ids,
            ["categ_id", "name", "default_code"]
        )
        
        # Verificar si algún producto es de fruta
        for prod in products:
            # Obtener nombre de categoría
            categ_name = ""
            if prod.get("categ_id"):
                categ_name = prod["categ_id"][1] if isinstance(prod["categ_id"], list) else str(prod["categ_id"])
            categ_upper = categ_name.upper()
            
            # Obtener nombre del producto
            prod_name = (prod.get("name") or "").upper()
            prod_code = (prod.get("default_code") or "").upper()
            
            # Verificar si está en categorías de productos
            if any(cat in categ_upper for cat in CATEGORIAS_PRODUCTOS):
                # Verificar keywords de fruta en nombre o código
                if any(kw in prod_name or kw in prod_code for kw in KEYWORDS_FRUTA):
                    return True
        
        return False
        
    except Exception:
        # En caso de error, asumir que NO es fruta
        return False


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
    
    # Obtener TC histórico desde res.currency.rate para USD
    def get_tc_historico(client, fecha: str) -> float:
        """Obtiene el TC histórico de USD para una fecha específica."""
        try:
            # Buscar rate de USD para esa fecha
            rates = client.search_read(
                "res.currency.rate",
                [
                    ("currency_id.name", "=", "USD"),
                    ("name", "<=", fecha)
                ],
                ["rate"],
                limit=1,
                order="name desc"
            )
            
            if rates and rates[0].get("rate", 0) > 0:
                return 1 / rates[0]["rate"]
            return 0
        except:
            return 0
    
    # Obtener fecha de OC desde el nombre de la línea
    def get_fecha_oc(client, nombre_linea: str) -> str:
        """Extrae el nombre de la OC y busca su fecha."""
        try:
            # Extraer OC del nombre (formato: "OC12345: [producto] descripcion")
            if ":" in nombre_linea:
                oc_nombre = nombre_linea.split(":")[0].strip()
                
                # Buscar la OC
                ocs = client.search_read(
                    "purchase.order",
                    [("name", "=", oc_nombre)],
                    ["date_order"],
                    limit=1
                )
                
                if ocs and ocs[0].get("date_order"):
                    return ocs[0]["date_order"][:10]
        except:
            pass
        return ""
    
    for fac in facturas:
        # FILTRO: Solo facturas que contengan productos de fruta
        invoice_line_ids = fac.get("invoice_line_ids", [])
        if not tiene_productos_fruta(client, invoice_line_ids):
            continue  # Saltar facturas sin productos de fruta
        
        lineas = []
        
        if invoice_line_ids:
            lines_data = client.read(
                "account.move.line",
                invoice_line_ids,
                [
                    "id", "name", "quantity", "price_unit",
                    "price_subtotal", "price_total",
                    "debit", "credit", "amount_currency",
                    "display_type", "product_id", "date"
                ]
            )
            
            for line in lines_data:
                # Saltar líneas de sección, notas o términos de pago
                if line.get("display_type") in ["line_section", "line_note", "payment_term"]:
                    continue
                
                # Obtener TC histórico de la OC específica de esta línea
                nombre_linea = line.get("name", "")
                fecha_oc = get_fecha_oc(client, nombre_linea)
                
                usd_subtotal = line.get("price_subtotal", 0) or 0
                
                if fecha_oc:
                    # Usar TC histórico de la fecha de la OC
                    tc_linea = get_tc_historico(client, fecha_oc)
                    clp_subtotal = usd_subtotal * tc_linea
                else:
                    # Fallback: usar debit actual si no se encuentra la OC
                    clp_subtotal = line.get("debit", 0) or 0
                    tc_linea = clp_subtotal / usd_subtotal if usd_subtotal > 0 else 0
                
                lineas.append({
                    "id": line["id"],
                    "nombre": nombre_linea,
                    "producto_id": line.get("product_id", [None, ""])[0] if line.get("product_id") else None,
                    "producto_nombre": line.get("product_id", [None, ""])[1] if line.get("product_id") else "",
                    "cantidad": line.get("quantity", 0),
                    "precio_usd": line.get("price_unit", 0),
                    "subtotal_usd": usd_subtotal,
                    "total_usd": line.get("price_total", 0) or 0,
                    "subtotal_clp": clp_subtotal,
                    "tc_implicito": tc_linea
                })
        
        # Calcular totales
        total_base_clp = sum(l["subtotal_clp"] for l in lineas)
        total_iva_clp = total_base_clp * 0.19
        total_con_iva_clp = total_base_clp + total_iva_clp
        
        # TC promedio de todas las líneas
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
        attachment_data = {
            "name": f"Proforma_{nombre_factura}.pdf",
            "type": "binary",
            "datas": pdf_base64,
            "res_model": "account.move",
            "res_id": factura_id,
            "mimetype": "application/pdf",
            "description": f"Proforma enviada por correo"
        }
        
        attachment_id = client.execute("ir.attachment", "create", [attachment_data])
        
        # Si retorna lista, extraer primer elemento
        if isinstance(attachment_id, list):
            attachment_id = attachment_id[0] if attachment_id else None
            
        if not attachment_id:
            raise Exception("No se pudo crear el adjunto en Odoo")
        
        # Crear y enviar correo
        asunto = f"Proforma {nombre_factura} - Rio Futuro"
        
        cuerpo_html = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <div style="background-color: #1B4F72; padding: 20px; text-align: center;">
                <h2 style="color: #FFFFFF; margin: 0; font-size: 24px;">Proforma de Proveedor</h2>
            </div>
            
            <div style="padding: 30px; background-color: #f9f9f9;">
                <p style="color: #333; font-size: 15px;">Estimado(a) <strong>{proveedor_nombre}</strong>,</p>
                
                <p style="color: #555; line-height: 1.6;">
                    Adjunto encontrará la proforma correspondiente a la factura <strong style="color: #1B4F72;">{nombre_factura}</strong>.
                </p>
                
                <div style="background-color: #E8F4F8; border-left: 4px solid #2E86AB; padding: 15px; margin: 20px 0;">
                    <p style="margin: 0; color: #333;"><strong>Detalle:</strong></p>
                    <ul style="color: #555; margin: 10px 0;">
                        <li><strong>Factura:</strong> {nombre_factura}</li>
                        <li><strong>Moneda:</strong> CLP (Pesos Chilenos)</li>
                    </ul>
                </div>
                
                <p style="color: #555; line-height: 1.6;">
                    Por favor revise el documento adjunto y no dude en contactarnos si tiene alguna consulta.
                </p>
                
                <p style="color: #333; margin-top: 30px;">Saludos cordiales,</p>
                <p style="color: #1B4F72; font-weight: bold; font-size: 16px; margin: 5px 0;">Rio Futuro Procesos</p>
            </div>
            
            <div style="background-color: #1B4F72; padding: 15px; text-align: center;">
                <p style="font-size: 11px; color: #FFFFFF; margin: 0;">
                    Este correo fue enviado automáticamente desde el sistema de gestión de Rio Futuro.
                </p>
            </div>
        </div>
        """
        
        # Crear mensaje de correo usando el servidor configurado en Odoo
        mail_data = {
            "subject": asunto,
            "body_html": cuerpo_html,
            "email_to": email_destino,
            "email_from": "notificaciones-rfp@riofuturo.cl",  # Servidor configurado en Odoo
            "attachment_ids": [(6, 0, [attachment_id])],  # Tupla para many2many
            "auto_delete": True
        }
        
        mail_id = client.execute("mail.mail", "create", [mail_data])
        
        # Si retorna lista, extraer primer elemento
        if isinstance(mail_id, list):
            mail_id = mail_id[0] if mail_id else None
        
        if not mail_id:
            raise Exception("No se pudo crear el correo en Odoo")
        
        # Enviar el correo (send no retorna valor útil, solo ejecutar)
        try:
            client.execute("mail.mail", "send", [mail_id])
        except Exception as e:
            # Si el error es por marshal None, ignorarlo (send fue exitoso)
            if "cannot marshal None" not in str(e):
                raise
        
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
        
        # message_post sin adjuntos (el adjunto ya está vinculado a la factura)
        try:
            client.execute(
                "account.move",
                "message_post",
                factura_id,
                body=mensaje_chatter,
                message_type="comment",
                subtype_xmlid="mail.mt_note"
            )
        except Exception as e:
            # Si el error es por marshal None, ignorarlo (message_post fue exitoso)
            if "cannot marshal None" not in str(e):
                raise
        
        return {
            "success": True,
            "mail_id": mail_id,
            "attachment_id": attachment_id,
            "email_destino": email_destino,
            "factura": nombre_factura
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}
