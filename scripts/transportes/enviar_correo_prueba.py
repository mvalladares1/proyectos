"""
Script para enviar un correo de prueba de proforma
IMPORTANTE: Este script envía un correo REAL a través de Odoo
Solo ejecutar cuando estés listo para probar el envío real
"""

import sys
import xmlrpc.client
from datetime import datetime

# Configuración de Odoo
URL = 'https://riofuturo.server98c6e.oerpondemand.net'
DB = 'riofuturo-master'

# Agregar path para importar templates
sys.path.insert(0, r'c:\new\RIO FUTURO\DASHBOARD\proyectos\pages\recepciones')
from email_templates import get_proforma_email_template

# ========================================
# CONFIGURACIÓN DE PRUEBA
# ========================================

# Credenciales - CAMBIAR SEGÚN USUARIO
USERNAME = input("Usuario Odoo (email): ").strip()
PASSWORD = input("Password Odoo: ").strip()

# Email de destino para prueba
EMAIL_DESTINO = input("\nEmail destino para prueba: ").strip()

# Datos de prueba
DATOS_PRUEBA = {
    'transportista': 'TRANSPORTES PRUEBA LIMITADA',
    'fecha_desde': '2026-01-01',
    'fecha_hasta': '2026-01-31',
    'cant_ocs': 3,
    'total_kms': 1380.0,
    'total_kilos': 39500.0,
    'total_costo': 690000.0
}

print("\n" + "=" * 80)
print("ENVÍO DE CORREO DE PRUEBA - PROFORMA DE FLETES")
print("=" * 80)

# Confirmar antes de enviar
print(f"\n⚠️  Se enviará un correo de PRUEBA a: {EMAIL_DESTINO}")
print(f"   Transportista: {DATOS_PRUEBA['transportista']}")
print(f"   Período: {DATOS_PRUEBA['fecha_desde']} al {DATOS_PRUEBA['fecha_hasta']}")
print(f"   Total: ${DATOS_PRUEBA['total_costo']:,.0f}")

confirmar = input("\n¿Deseas continuar? (SI/NO): ").strip().upper()

if confirmar != 'SI':
    print("\n❌ Envío cancelado por el usuario")
    sys.exit(0)

try:
    # Conectar a Odoo
    print("\n1. Conectando a Odoo...")
    common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
    uid = common.authenticate(DB, USERNAME, PASSWORD, {})
    
    if not uid:
        print("   ❌ Error de autenticación")
        sys.exit(1)
    
    print(f"   ✅ Conectado como usuario ID: {uid}")
    
    models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')
    
    # Generar template de email
    print("\n2. Generando template de email...")
    email_data = get_proforma_email_template(
        transportista=DATOS_PRUEBA['transportista'],
        fecha_desde=DATOS_PRUEBA['fecha_desde'],
        fecha_hasta=DATOS_PRUEBA['fecha_hasta'],
        cant_ocs=DATOS_PRUEBA['cant_ocs'],
        total_kms=DATOS_PRUEBA['total_kms'],
        total_kilos=DATOS_PRUEBA['total_kilos'],
        total_costo=DATOS_PRUEBA['total_costo'],
        email_remitente="finanzas@riofuturo.cl",
        telefono_contacto="+56 2 2345 6789"
    )
    
    print(f"   ✅ Template generado")
    print(f"   📧 Asunto: {email_data['subject']}")
    print(f"   📊 Tamaño HTML: {len(email_data['body_html']):,} caracteres")
    
    # Crear correo en Odoo
    print("\n3. Creando correo en Odoo...")
    mail_id = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.mail', 'create',
        [{
            'subject': f"[PRUEBA] {email_data['subject']}",
            'email_to': EMAIL_DESTINO,
            'body_html': email_data['body_html'],
            'auto_delete': False  # No borrar automáticamente
        }]
    )
    
    print(f"   ✅ Correo creado con ID: {mail_id}")
    
    # Enviar correo
    print("\n4. Enviando correo...")
    models.execute_kw(
        DB, uid, PASSWORD,
        'mail.mail', 'send',
        [[mail_id]]
    )
    
    print(f"   ✅ Correo enviado!")
    
    # Verificar estado del correo
    print("\n5. Verificando estado del correo...")
    mail_info = models.execute_kw(
        DB, uid, PASSWORD,
        'mail.mail', 'read',
        [mail_id],
        {'fields': ['state', 'email_to', 'subject', 'failure_reason']}
    )
    
    if mail_info:
        estado = mail_info[0].get('state', 'unknown')
        print(f"   📊 Estado: {estado}")
        
        if estado == 'sent':
            print(f"   ✅ El correo fue enviado exitosamente")
        elif estado == 'exception':
            print(f"   ❌ Error al enviar: {mail_info[0].get('failure_reason', 'Unknown')}")
        else:
            print(f"   ⏳ Estado: {estado}")
    
    print("\n" + "=" * 80)
    print("RESUMEN DEL ENVÍO")
    print("=" * 80)
    print(f"✅ Correo de prueba enviado a: {EMAIL_DESTINO}")
    print(f"📧 ID del correo en Odoo: {mail_id}")
    print(f"📊 Asunto: [PRUEBA] {email_data['subject']}")
    print(f"\n💡 Puedes verificar el correo en:")
    print(f"   - Tu bandeja de entrada: {EMAIL_DESTINO}")
    print(f"   - Odoo → Configuración → Técnico → Email → Emails (ID: {mail_id})")
    print("\n⚠️  IMPORTANTE:")
    print("   - Este es un correo de PRUEBA (incluye [PRUEBA] en el asunto)")
    print("   - No incluye PDF adjunto (solo el template HTML)")
    print("   - Revisa spam/promociones si no lo ves en inbox")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
