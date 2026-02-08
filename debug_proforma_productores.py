"""
Script de Debug: Validación de Cálculos de Proformas USD → CLP
=============================================================

Este script valida que los cálculos de conversión USD → CLP sean correctos
para asegurar que se pague el monto justo a los productores.

Propósito:
- Evitar pérdidas de dinero para la empresa
- Evitar reclamos de productores por pagos incorrectos
- Documentar cálculos para auditoría

Uso:
    python debug_proforma_productores.py
"""

import sys
import os
from datetime import datetime
from shared.odoo_client import OdooClient
from decimal import Decimal, ROUND_HALF_UP
import json

# Categorías que NO son productos de fruta (excluir)
CATEGORIAS_EXCLUIDAS = [
    "INVENTARIABLES", "BANDEJAS", "ACTIVO", "SERVICIOS",
    "EQUIPOS", "MUEBLES", "EJEMPLODS", "OTROS", "ALL1",
    "BANCO"  # Excluir facturas de bancos
]

# Configuración
FACTURA_ID = None  # Se puede especificar una factura específica o None para buscar
FECHA_DESDE = "2026-02-01"  # Solo febrero 2026
FECHA_HASTA = "2026-02-05"
OUTPUT_FILE = f"debug_proforma_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
ESTADO = "draft"  # draft = borradores que están pendientes de validar


def get_tc_historico(client: OdooClient, fecha_oc: str) -> float:
    """
    Obtiene el TC histórico de USD a CLP para una fecha específica.
    Usa res.currency.rate de Odoo.
    """
    try:
        # Buscar USD
        usd_currency = client.search_read(
            "res.currency",
            [("name", "=", "USD")],
            ["id"],
            limit=1
        )
        
        if not usd_currency:
            print("⚠️  No se encontró moneda USD en Odoo")
            return 0.0
        
        usd_id = usd_currency[0]["id"]
        
        # Buscar rate más cercano a la fecha
        rates = client.search_read(
            "res.currency.rate",
            [
                ("currency_id", "=", usd_id),
                ("name", "<=", fecha_oc)
            ],
            ["name", "rate"],
            order="name desc",
            limit=1
        )
        
        if rates and rates[0].get("rate"):
            # La rate en Odoo es 1/TC (ej: 0.00116 para TC 860)
            tc = 1.0 / rates[0]["rate"]
            return round(tc, 2)
        
        print(f"⚠️  No se encontró TC para fecha {fecha_oc}")
        return 0.0
        
    except Exception as e:
        print(f"❌ Error obteniendo TC: {e}")
        return 0.0


def extraer_oc_nombre(descripcion: str) -> str:
    """Extrae el nombre de OC de la descripción de la línea."""
    if not descripcion or descripcion is False:
        return ""
    if ":" in str(descripcion):
        return str(descripcion).split(":")[0].strip()
    return ""


def tiene_productos_fruta(client: OdooClient, invoice_line_ids: list) -> bool:
    """
    Verifica si una factura contiene productos de fruta.
    
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
            ["product_id", "display_type"]
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
        
        # Leer productos con su categoría
        products = client.read(
            "product.product",
            product_ids,
            ["categ_id"]
        )
        
        # Verificar si algún producto es de fruta
        for prod in products:
            if prod.get("categ_id"):
                categ_name = prod["categ_id"][1] if isinstance(prod["categ_id"], list) else str(prod["categ_id"])
                categ_upper = categ_name.upper()
                
                # Si NO está en categorías excluidas, es fruta
                if not any(excl in categ_upper for excl in CATEGORIAS_EXCLUIDAS):
                    return True
        
        return False
        
    except Exception:
        # En caso de error, asumir que NO es fruta
        return False


def debug_factura(client: OdooClient, factura_id: int):
    """
    Analiza una factura específica y genera reporte detallado.
    """
    print(f"\n{'='*80}")
    print(f"🔍 DEBUG FACTURA ID: {factura_id}")
    print(f"{'='*80}\n")
    
    # Obtener factura
    facturas = client.read(
        "account.move",
        [factura_id],
        [
            "id", "name", "ref", "partner_id", "invoice_date", 
            "amount_untaxed", "amount_tax", "amount_total",
            "amount_untaxed_signed", "amount_total_signed",
            "invoice_line_ids", "currency_id", "invoice_origin"
        ]
    )
    
    if not facturas:
        print(f"❌ No se encontró factura con ID {factura_id}")
        return None
    
    factura = facturas[0]
    
    # Información básica
    info = {
        "factura_id": factura["id"],
        "factura_nombre": factura.get("name", ""),
        "factura_ref": factura.get("ref", ""),
        "proveedor": factura["partner_id"][1] if isinstance(factura["partner_id"], list) else str(factura["partner_id"]),
        "fecha_factura": factura.get("invoice_date", ""),
        "moneda": factura["currency_id"][1] if isinstance(factura["currency_id"], list) else str(factura["currency_id"]),
        "origen": factura.get("invoice_origin", ""),
        "totales_odoo": {
            "base_usd": factura.get("amount_untaxed", 0),
            "iva_usd": factura.get("amount_tax", 0),
            "total_usd": factura.get("amount_total", 0),
            "base_clp_signed": abs(factura.get("amount_untaxed_signed", 0)),
            "total_clp_signed": abs(factura.get("amount_total_signed", 0))
        },
        "lineas": [],
        "analisis": {}
    }
    
    print(f"📄 Factura: {info['factura_nombre']}")
    print(f"🏢 Proveedor: {info['proveedor']}")
    print(f"📅 Fecha: {info['fecha_factura']}")
    print(f"💵 Moneda: {info['moneda']}")
    print(f"📋 Origen: {info['origen']}")
    print(f"\n{'─'*80}\n")
    
    # Obtener líneas
    line_ids = factura.get("invoice_line_ids", [])
    if not line_ids:
        print("⚠️  Factura sin líneas")
        return info
    
    lineas = client.read(
        "account.move.line",
        line_ids,
        ["id", "name", "quantity", "price_unit", "price_subtotal", "currency_id", "debit", "credit"]
    )
    
    print(f"📦 Analizando {len(lineas)} líneas:\n")
    
    # Cache de TCs por fecha OC
    tc_cache = {}
    
    # Procesar cada línea
    total_base_calculada = 0.0
    
    for idx, linea in enumerate(lineas, 1):
        linea_info = {
            "numero": idx,
            "id": linea["id"],
            "descripcion": linea.get("name", ""),
            "cantidad_kg": linea.get("quantity", 0),
            "precio_unit_usd": linea.get("price_unit", 0),
            "subtotal_usd": linea.get("price_subtotal", 0),
            "debit_odoo": linea.get("debit", 0),  # CLP que usó Odoo
            "credit_odoo": linea.get("credit", 0)
        }
        
        # Extraer OC
        oc_nombre = extraer_oc_nombre(linea_info["descripcion"])
        linea_info["oc_nombre"] = oc_nombre
        
        # Obtener fecha de OC y TC
        fecha_oc = None
        tc = 0.0
        
        if oc_nombre:
            # Buscar OC
            ocs = client.search_read(
                "purchase.order",
                [("name", "=", oc_nombre)],
                ["date_order"],
                limit=1
            )
            
            if ocs and ocs[0].get("date_order"):
                fecha_oc = ocs[0]["date_order"][:10]
                linea_info["fecha_oc"] = fecha_oc
                
                # Usar cache de TC
                if fecha_oc not in tc_cache:
                    tc_cache[fecha_oc] = get_tc_historico(client, fecha_oc)
                
                tc = tc_cache[fecha_oc]
            else:
                linea_info["fecha_oc"] = None
                linea_info["error"] = f"No se encontró OC {oc_nombre}"
        else:
            linea_info["fecha_oc"] = None
            linea_info["error"] = "No se pudo extraer nombre de OC"
        
        linea_info["tc_historico"] = tc
        
        # Calcular CLP con TC histórico
        subtotal_clp = linea_info["subtotal_usd"] * tc
        linea_info["subtotal_clp"] = round(subtotal_clp, 2)
        
        # Calcular TC que usó Odoo (debit / subtotal_usd)
        tc_odoo = linea_info["debit_odoo"] / linea_info["subtotal_usd"] if linea_info["subtotal_usd"] > 0 else 0
        linea_info["tc_odoo"] = round(tc_odoo, 2)
        
        # Diferencia entre TCs
        diff_tc = abs(tc - tc_odoo)
        diff_clp = abs(linea_info["subtotal_clp"] - linea_info["debit_odoo"])
        
        total_base_calculada += subtotal_clp
        
        # Mostrar línea con validación de OC y TC
        print(f"Línea {idx}:")
        print(f"  Descripción: {linea_info['descripcion'][:70]}")
        print(f"  OC: {oc_nombre or 'N/A'} | Fecha OC: {fecha_oc or 'N/A'}")
        print(f"  Cantidad: {linea_info['cantidad_kg']:,.2f} KG")
        print(f"  Precio Unit: ${linea_info['precio_unit_usd']:,.2f} USD")
        print(f"  Subtotal USD: ${linea_info['subtotal_usd']:,.2f}")
        print(f"  ──────────────────────────────────────────")
        
        if tc > 0 and fecha_oc:
            print(f"  ✅ TC Histórico ({fecha_oc}): {tc:,.2f}")
            print(f"  💰 Subtotal CLP: ${linea_info['subtotal_clp']:,.0f}")
            linea_info["valida"] = True
        else:
            print(f"  ❌ TC NO DISPONIBLE (sin OC o fecha)")
            print(f"  💰 Subtotal CLP: $0")
            linea_info["valida"] = False
        
        if "error" in linea_info:
            print(f"  ⚠️  {linea_info['error']}")
            linea_info["valida"] = False
        
        print()
        
        info["lineas"].append(linea_info)
    
    # Análisis final - VALIDACIÓN DE OCs Y TC
    print(f"\n{'='*80}")
    print(f"📊 VALIDACIÓN DE PAGO AL PRODUCTOR")
    print(f"{'='*80}\n")
    
    base_calculada = round(total_base_calculada, 2)
    lineas_validas = [l for l in info["lineas"] if l.get("valida", False)]
    lineas_invalidas = [l for l in info["lineas"] if not l.get("valida", False)]
    
    print(f"Líneas con OC y TC válido: {len(lineas_validas)}/{len(info['lineas'])}")
    
    if lineas_invalidas:
        print(f"\n⚠️  Líneas sin TC válido:")
        for l in lineas_invalidas:
            print(f"  - Línea {l['numero']}: {l['descripcion'][:50]}")
            print(f"    Monto USD: ${l['subtotal_usd']:,.2f}")
    
    print(f"\n💰 TOTAL A PAGAR AL PRODUCTOR:")
    print(f"Base CLP (con TC histórico de cada OC): ${base_calculada:,.0f}")
    
    # Calcular totales con IVA
    iva_calculado = base_calculada * 0.19
    total_calculado = base_calculada + iva_calculado
    
    print(f"IVA 19%: ${iva_calculado:,.0f}")
    print(f"Total CLP: ${total_calculado:,.0f}")
    print()
    
    # Veredicto basado SOLO en si todas las líneas tienen OC y TC
    info["analisis"] = {
        "base_clp_calculada": base_calculada,
        "lineas_validas": len(lineas_validas),
        "lineas_invalidas": len(lineas_invalidas),
        "iva_calculado": round(iva_calculado, 2),
        "total_calculado": round(total_calculado, 2),
        "tc_cache": tc_cache
    }
    
    if len(lineas_invalidas) == 0:
        print(f"✅ VEREDICTO: Todas las líneas tienen OC y TC histórico válido")
        print(f"   El monto a pagar es correcto según TC histórico de cada OC")
        info["analisis"]["veredicto"] = "OK"
    else:
        print(f"❌ VEREDICTO: HAY LÍNEAS SIN OC O TC VÁLIDO")
        print(f"\n🔍 Acciones requeridas:")
        print(f"  1. Verificar que todas las líneas tengan formato 'OC####: descripción'")
        print(f"  2. Validar que las OCs existan en el sistema")
        print(f"  3. Confirmar fechas de las OCs")
        info["analisis"]["veredicto"] = "ERROR"
    
    print(f"{'='*80}\n")
    
    return info


def main():
    """Función principal."""
    print("\n" + "="*80)
    print("🔍 VALIDACIÓN DE PROFORMAS USD → CLP")
    print("Verificación de TC Histórico para Pago Correcto a Productores")
    print("="*80 + "\n")
    
    # Obtener credenciales de variables de entorno
    username = os.getenv("ODOO_USER")
    password = os.getenv("ODOO_PASSWORD")
    
    if not username or not password:
        print("❌ Credenciales no encontradas en .env")
        print("Configure ODOO_USER y ODOO_PASSWORD en el archivo .env")
        return
    
    try:
        client = OdooClient(username=username, password=password)
        print("✅ Conectado a Odoo\n")
    except Exception as e:
        print(f"❌ Error conectando a Odoo: {e}")
        return
    
    # Buscar facturas
    if FACTURA_ID:
        factura_ids = [FACTURA_ID]
    else:
        if ESTADO:
            estado_texto = "borrador" if ESTADO == "draft" else "validadas"
            print(f"Buscando facturas {estado_texto} USD entre {FECHA_DESDE} y {FECHA_HASTA}...\n")
        else:
            print(f"Buscando TODAS las facturas USD entre {FECHA_DESDE} y {FECHA_HASTA}...\n")
        
        # Construir dominio IGUAL QUE EN EL DASHBOARD
        dominio = [
            ("move_type", "=", "in_invoice"),  # Facturas de proveedor
            ("currency_id.name", "=", "USD"),
        ]
        
        if ESTADO:
            dominio.append(("state", "=", ESTADO))
        
        # IMPORTANTE: El dashboard busca por create_date, NO por invoice_date
        if FECHA_DESDE:
            dominio.append(("create_date", ">=", FECHA_DESDE))
        
        if FECHA_HASTA:
            dominio.append(("create_date", "<=", f"{FECHA_HASTA} 23:59:59"))
        
        facturas = client.search_read(
            "account.move",
            dominio,
            ["id", "name", "partner_id", "state", "invoice_date", "create_date", "invoice_line_ids"],
            limit=100,
            order="create_date desc"
        )
        
        if not facturas:
            print("❌ No se encontraron facturas")
            return
        
        # FILTRO: Solo facturas que contengan productos de fruta
        print(f"📋 Filtrando facturas con productos de fruta...")
        facturas_fruta = []
        for f in facturas:
            if tiene_productos_fruta(client, f.get("invoice_line_ids", [])):
                facturas_fruta.append(f)
        
        facturas = facturas_fruta
        
        if not facturas:
            print("❌ No se encontraron facturas de productores con fruta")
            return
        
        print(f"Se encontraron {len(facturas)} facturas:\n")
        for idx, f in enumerate(facturas, 1):
            partner_name = f["partner_id"][1] if isinstance(f["partner_id"], list) else str(f["partner_id"])
            estado = f.get("state", "")
            fecha = f.get("invoice_date", "")
            estado_emoji = "📝" if estado == "draft" else "✅"
            print(f"{idx}. {estado_emoji} {f['name']} - {partner_name} ({fecha})")
        
        print()
        seleccion = input("Selecciona número de factura a analizar (o 'todas' para todas): ").strip()
        
        if seleccion.lower() == "todas":
            factura_ids = [f["id"] for f in facturas]
        else:
            try:
                idx = int(seleccion) - 1
                if 0 <= idx < len(facturas):
                    factura_ids = [facturas[idx]["id"]]
                else:
                    print("❌ Selección inválida")
                    return
            except ValueError:
                print("❌ Selección inválida")
                return
    
    # Analizar facturas
    resultados = []
    
    for factura_id in factura_ids:
        resultado = debug_factura(client, factura_id)
        if resultado:
            resultados.append(resultado)
    
    # Guardar resultados
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Resultados guardados en: {OUTPUT_FILE}")
    
    # Resumen
    print(f"\n{'='*80}")
    print(f"📊 RESUMEN DE VALIDACIÓN")
    print(f"{'='*80}\n")
    print(f"Total facturas analizadas: {len(resultados)}")
    
    ok = sum(1 for r in resultados if r["analisis"]["veredicto"] == "OK")
    error = sum(1 for r in resultados if r["analisis"]["veredicto"] == "ERROR")
    
    print(f"✅ Válidas (todas las líneas con OC y TC): {ok}")
    print(f"❌ Con errores (líneas sin OC o TC): {error}")
    
    if error > 0:
        print(f"\n⚠️  HAY {error} FACTURAS CON LÍNEAS SIN OC O TC VÁLIDO")
        print("Revisar archivo de debug para detalles")
    else:
        print(f"\n✅ TODAS LAS FACTURAS SON VÁLIDAS")
        print("Los montos a pagar usan TC histórico correcto de cada OC")
    
    print()


if __name__ == "__main__":
    main()
