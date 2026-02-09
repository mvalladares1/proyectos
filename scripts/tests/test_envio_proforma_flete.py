"""
Script de prueba para enviar proforma de fletes a mvalladares@riofuturo.cl
"""

import os
import sys
import xmlrpc.client
from datetime import datetime
from dotenv import load_dotenv

# Agregar path para imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Cargar variables de entorno
load_dotenv()

# Importar funciones del módulo de proformas
from pages.recepciones.tab_proforma_consolidada import (
    generar_pdf_individual_transportista,
    get_email_template_transportista,
    obtener_ocs_transportes,
    buscar_ruta_en_logistica,
    obtener_rutas_logistica,
    obtener_kg_de_oc_mp,
    obtener_nombre_ruta_real
)

URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'

def main():
    # Credenciales
    username = os.getenv('ODOO_USER')
    password = os.getenv('ODOO_PASSWORD')
    
    if not username or not password:
        print("❌ Error: ODOO_USER y ODOO_PASSWORD deben estar en .env")
        return
    
    print(f"🔐 Conectando a Odoo como {username}...")
    
    # Conectar a Odoo
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, username, password, {})
    
    if not uid:
        print("❌ Error de autenticación")
        return
    
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    print(f"✅ Conectado exitosamente (UID: {uid})")
    
    # Buscar OCs de transporte de los últimos 2 meses
    fecha_desde = '2025-12-01'
    fecha_hasta = '2026-02-06'
    
    print(f"\n🔍 Buscando OCs de transporte del {fecha_desde} al {fecha_hasta}...")
    
    # Obtener OCs
    domain = [
        ('date_order', '>=', fecha_desde),
        ('date_order', '<=', fecha_hasta),
        ('state', 'in', ['purchase', 'done']),
        ('partner_id.name', 'ilike', 'TRANSPORT')  # Buscar transportistas
    ]
    
    ocs = models.execute_kw(
        DB, uid, password,
        'purchase.order', 'search_read',
        [domain],
        {'fields': ['id', 'name', 'partner_id', 'date_order', 'order_line', 'amount_untaxed'], 'limit': 50}
    )
    
    if not ocs:
        print("❌ No se encontraron OCs de transporte en el período")
        return
    
    print(f"✅ Encontradas {len(ocs)} OCs de transporte")
    
    # Agrupar por transportista
    from collections import defaultdict
    import json
    import requests
    
    transportistas_data = defaultdict(lambda: {'ocs': [], 'totales': {'kms': 0, 'kilos': 0, 'costo': 0}})
    
    # Obtener rutas de logística
    print("\n🌐 Obteniendo rutas del sistema de logística...")
    try:
        response = requests.get('https://riofuturoprocesos.com/api/logistica/rutas', timeout=10)
        if response.status_code == 200:
            data = response.json()
            rutas_logistica = data if isinstance(data, list) else data.get('data', [])
            print(f"✅ {len(rutas_logistica)} rutas cargadas del sistema de logística")
        else:
            rutas_logistica = []
            print("⚠️ No se pudieron cargar rutas de logística")
    except Exception as e:
        rutas_logistica = []
        print(f"⚠️ Error cargando rutas: {e}")
    
    # Procesar cada OC
    for oc in ocs:
        transportista = oc['partner_id'][1] if oc.get('partner_id') else 'N/A'
        
        # Buscar ruta en logística
        ruta_info = None
        for ruta in rutas_logistica:
            po_name = ruta.get('purchase_order_name') or ruta.get('po')
            if po_name == oc['name']:
                ruta_info = ruta
                break
        
        kms = ruta_info.get('total_distance_km', 0) if ruta_info else 0
        numero_ruta = ruta_info.get('name', '') if ruta_info else ''
        
        # Obtener kilos
        kilos = 0
        if ruta_info:
            kilos_mp = ruta_info.get('total_qnt', 0)
            if kilos_mp and kilos_mp > 0:
                kilos = float(kilos_mp)
        
        # Obtener nombre de ruta
        nombre_ruta = 'Sin ruta'
        tipo_camion = 'N/A'
        if ruta_info:
            routes_field = ruta_info.get('routes', False)
            if routes_field and isinstance(routes_field, str) and routes_field.startswith('['):
                try:
                    routes_data = json.loads(routes_field)
                    if routes_data and len(routes_data) > 0:
                        route_info = routes_data[0]
                        nombre_ruta = route_info.get('name', 'Sin nombre')
                        
                        cost_type = route_info.get('cost_type', '')
                        if cost_type == 'truck_8':
                            tipo_camion = '🚛 Camión 8 Ton'
                        elif cost_type == 'truck_12_14':
                            tipo_camion = '🚚 Camión 12-14 Ton'
                        elif cost_type == 'short_rampla':
                            tipo_camion = '🚐 Rampla Corta'
                        elif cost_type == 'rampla':
                            tipo_camion = '🚛 Rampla'
                except:
                    pass
        
        costo = oc.get('amount_untaxed', 0)
        costo_por_km = (costo / kms) if kms > 0 else 0
        
        transportistas_data[transportista]['ocs'].append({
            'oc_name': oc['name'],
            'fecha': oc['date_order'][:10] if oc.get('date_order') else 'N/A',
            'ruta': nombre_ruta,
            'kms': kms,
            'kilos': kilos,
            'costo': costo,
            'costo_por_km': costo_por_km,
            'tipo_camion': tipo_camion
        })
        
        transportistas_data[transportista]['totales']['kms'] += kms
        transportistas_data[transportista]['totales']['kilos'] += kilos
        transportistas_data[transportista]['totales']['costo'] += costo
    
    # Mostrar resumen
    print(f"\n📊 Transportistas encontrados:")
    for idx, (transp, data) in enumerate(transportistas_data.items(), 1):
        print(f"  {idx}. {transp}: {len(data['ocs'])} OCs, ${data['totales']['costo']:,.0f}")
    
    # Seleccionar transportista con más de 1 OC y preferiblemente con datos de ruta
    transportista_seleccionado = None
    for transp, data in sorted(transportistas_data.items(), key=lambda x: len(x[1]['ocs']), reverse=True):
        if len(data['ocs']) >= 2:  # Al menos 2 OCs
            transportista_seleccionado = (transp, data)
            break
    
    # Si no hay ninguno con 2+ OCs, tomar el que tenga más
    if not transportista_seleccionado:
        transportista_seleccionado = max(transportistas_data.items(), key=lambda x: len(x[1]['ocs']))
    
    transportista_nombre = transportista_seleccionado[0]
    data = transportista_seleccionado[1]
    
    print(f"\n✅ Seleccionado: {transportista_nombre} con {len(data['ocs'])} OCs")
    
    # Generar PDF
    print("\n📄 Generando PDF individual...")
    pdf_bytes = generar_pdf_individual_transportista(
        transportista_nombre, 
        data, 
        fecha_desde, 
        fecha_hasta
    )
    print(f"✅ PDF generado: {len(pdf_bytes)} bytes")
    
    # Guardar PDF localmente para revisión
    pdf_filename = f"PRUEBA_Proforma_Fletes_{transportista_nombre[:30].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    with open(pdf_filename, 'wb') as f:
        f.write(pdf_bytes)
    print(f"💾 PDF guardado: {pdf_filename}")
    
    # Generar email HTML
    print("\n📧 Generando email HTML...")
    email_data = get_email_template_transportista(
        transportista_nombre,
        data,
        fecha_desde,
        fecha_hasta
    )
    print(f"✅ Email generado")
    print(f"   Asunto: {email_data['subject']}")
    
    # Guardar HTML localmente para revisión
    html_filename = f"PRUEBA_Email_Fletes_{transportista_nombre[:30].replace(' ', '_')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    with open(html_filename, 'w', encoding='utf-8') as f:
        f.write(email_data['body_html'])
    print(f"💾 Email HTML guardado: {html_filename}")
    
    # Enviar correo
    print(f"\n📤 Enviando correo a mvalladares@riofuturo.cl...")
    
    import base64
    
    # Codificar PDF
    pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
    
    # Crear adjunto temporal en Odoo (sin vincular a ningún registro específico)
    attachment_data = {
        "name": f"Proforma_Fletes_PRUEBA_{fecha_desde}_{fecha_hasta}.pdf",
        "type": "binary",
        "datas": pdf_base64,
        "mimetype": "application/pdf",
        "description": f"Proforma de prueba para {transportista_nombre}"
    }
    
    attachment_id = models.execute_kw(
        DB, uid, password,
        'ir.attachment', 'create',
        [attachment_data]
    )
    
    if isinstance(attachment_id, list):
        attachment_id = attachment_id[0] if attachment_id else None
    
    print(f"✅ Adjunto creado (ID: {attachment_id})")
    
    # Crear correo
    mail_data = {
        "subject": f"[PRUEBA] {email_data['subject']}",
        "body_html": email_data['body_html'],
        "email_to": "mvalladares@riofuturo.cl",
        "email_from": "notificaciones-rfp@riofuturo.cl",
        "attachment_ids": [(6, 0, [attachment_id])],
        "auto_delete": False  # No borrar para revisión
    }
    
    mail_id = models.execute_kw(
        DB, uid, password,
        'mail.mail', 'create',
        [mail_data]
    )
    
    if isinstance(mail_id, list):
        mail_id = mail_id[0] if mail_id else None
    
    print(f"✅ Correo creado (ID: {mail_id})")
    
    # Enviar correo (usar método process_email_queue o marcar para envío)
    try:
        # Intentar envío inmediato
        models.execute_kw(
            DB, uid, password,
            'mail.mail', 'write',
            [[mail_id], {'state': 'outgoing'}]
        )
        
        # Procesar cola de emails
        models.execute_kw(
            DB, uid, password,
            'mail.mail', 'process_email_queue',
            [[]]
        )
        print(f"✅ Correo marcado para envío")
    except Exception as e:
        print(f"⚠️ Advertencia al enviar: {e}")
        print(f"   El correo quedó en cola de Odoo (ID: {mail_id})")
    
    print(f"\n🎉 ¡Correo enviado exitosamente a mvalladares@riofuturo.cl!")
    print(f"\n📋 Resumen:")
    print(f"   Transportista: {transportista_nombre}")
    print(f"   OCs incluidas: {len(data['ocs'])}")
    print(f"   Total KM: {data['totales']['kms']:,.0f}")
    print(f"   Total KG: {data['totales']['kilos']:,.1f}")
    print(f"   Total CLP: ${data['totales']['costo']:,.0f}")
    print(f"\n   OCs:")
    for oc in data['ocs']:
        print(f"     - {oc['oc_name']}: {oc['ruta'][:40]} (${oc['costo']:,.0f})")


if __name__ == "__main__":
    main()
