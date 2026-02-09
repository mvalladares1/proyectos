"""
Debug: probar creación de adjuntos en Odoo
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from shared.odoo_client import OdooClient
import base64

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

client = OdooClient(username=USERNAME, password=PASSWORD)

# Crear PDF de prueba
pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

print("1. Probando creación de adjunto...")
try:
    attachment_data = {
        "name": "test.pdf",
        "type": "binary",
        "datas": pdf_base64,
        "mimetype": "application/pdf",
        "description": "Test"
    }
    
    result = client.execute("ir.attachment", "create", [attachment_data])
    print(f"   Resultado: {result}")
    print(f"   Tipo: {type(result)}")
    
except Exception as e:
    print(f"   Error: {e}")
    import traceback
    traceback.print_exc()
