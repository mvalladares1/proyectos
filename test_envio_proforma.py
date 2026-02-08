"""
Test de envío de proforma a correo de prueba
Envía la proforma FAC 000001 a mvalladares@riofuturo.cl
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from backend.services.proforma_ajuste_service import get_facturas_borrador, enviar_proforma_email
import streamlit as st

# Credenciales (API Key)
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

print("=" * 70)
print("🧪 TEST: Envío de Proforma a Correo de Prueba")
print("=" * 70)

# 1. Buscar la factura FAC 000001
print("\n1️⃣ Buscando factura FAC 000001...")
try:
    facturas = get_facturas_borrador(USERNAME, PASSWORD)
    
    factura_test = None
    for f in facturas:
        if f['nombre'] == 'FAC 000001':
            factura_test = f
            break
    
    if not factura_test:
        print("❌ No se encontró la factura FAC 000001")
        print(f"   Facturas disponibles: {', '.join([f['nombre'] for f in facturas[:5]])}")
        sys.exit(1)
    
    print(f"✅ Factura encontrada:")
    print(f"   ID: {factura_test['id']}")
    print(f"   Nombre: {factura_test['nombre']}")
    print(f"   Proveedor: {factura_test['proveedor_nombre']}")
    print(f"   Total USD: ${factura_test['total_usd']:,.2f}")
    print(f"   Total CLP: ${factura_test['total_clp']:,.0f}")
    print(f"   Líneas: {factura_test['num_lineas']}")
    
except Exception as e:
    print(f"❌ Error obteniendo factura: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Generar PDF usando la función del módulo oficial
print("\n2️⃣ Generando PDF...")

# Inicializar session_state para que la función pueda acceder a credenciales
st.session_state['username'] = USERNAME
st.session_state['password'] = PASSWORD

# Importar la función de generación de PDF del módulo oficial
from pages.recepciones.tab_ajuste_proformas import _generar_pdf_proforma

try:
    pdf_bytes = _generar_pdf_proforma(factura_test)
    print(f"✅ PDF generado: {len(pdf_bytes)} bytes")
except Exception as e:
    print(f"❌ Error generando PDF: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Enviar por correo
print("\n3️⃣ Enviando proforma a mvalladares@riofuturo.cl...")

try:
    resultado = enviar_proforma_email(
        username=USERNAME,
        password=PASSWORD,
        factura_id=factura_test['id'],
        email_destino="mvalladares@riofuturo.cl",  # EMAIL DE PRUEBA
        pdf_bytes=pdf_bytes,
        nombre_factura=factura_test['nombre'],
        proveedor_nombre=factura_test['proveedor_nombre']
    )
    
    if resultado.get("success"):
        print(f"✅ Proforma enviada exitosamente!")
        print(f"   Mail ID: {resultado.get('mail_id')}")
        print(f"   Attachment ID: {resultado.get('attachment_id')}")
        print(f"   Destinatario: {resultado.get('email_destino')}")
        print("\n📧 Revisa tu correo: mvalladares@riofuturo.cl")
        print("   Asunto: Proforma FAC 000001 - Rio Futuro")
    else:
        print(f"❌ Error al enviar: {resultado.get('error')}")
        
except Exception as e:
    print(f"❌ Error: {str(e)}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ Test completado")
print("=" * 70)
