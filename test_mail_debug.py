"""
Debug paso a paso del envío de email
"""
import sys
sys.path.insert(0, r"c:\new\RIO FUTURO\DASHBOARD\proyectos")

from shared.odoo_client import OdooClient
import base64

USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

client = OdooClient(username=USERNAME, password=PASSWORD)

# PDF de prueba
pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
pdf_base64 = base64.b64encode(pdf_content).decode('utf-8')

print("=" * 70)
print("TEST PASO A PASO")
print("=" * 70)

# 1. Crear adjunto
print("\n1️⃣ Creando adjunto...")
try:
    attachment_data = {
        "name": "test_proforma.pdf",
        "type": "binary",
        "datas": pdf_base64,
        "res_model": "account.move",
        "res_id": 281836,  # FAC 000001
        "mimetype": "application/pdf",
        "description": "Test"
    }
    
    attachment_result = client.execute("ir.attachment", "create", [attachment_data])
    print(f"   Resultado: {attachment_result}")
    print(f"   Tipo: {type(attachment_result)}")
    
    if isinstance(attachment_result, list) and attachment_result:
        attachment_id = attachment_result[0]
        print(f"   ✅ Adjunto creado: ID {attachment_id}")
    else:
        print(f"   ❌ Error: resultado inesperado")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Crear mail
print("\n2️⃣ Creando mail...")
try:
    mail_data = {
        "subject": "Test Proforma",
        "body_html": "<p>Test de proforma</p>",
        "email_to": "mvalladares@riofuturo.cl",
        "email_from": "notificaciones-rfp@riofuturo.cl",
        "attachment_ids": [(6, 0, [attachment_id])],
        "auto_delete": True
    }
    
    mail_result = client.execute("mail.mail", "create", [mail_data])
    print(f"   Resultado: {mail_result}")
    print(f"   Tipo: {type(mail_result)}")
    
    if isinstance(mail_result, list) and mail_result:
        mail_id = mail_result[0]
        print(f"   ✅ Mail creado: ID {mail_id}")
    else:
        print(f"   ❌ Error: resultado inesperado")
        sys.exit(1)
        
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Enviar mail
print("\n3️⃣ Enviando mail...")
try:
    send_result = client.execute("mail.mail", "send", [mail_id])
    print(f"   Resultado: {send_result}")
    print(f"   Tipo: {type(send_result)}")
    print(f"   ✅ Mail enviado")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Message post
print("\n4️⃣ Posteando mensaje en chatter...")
try:
    post_result = client.execute(
        "account.move",
        "message_post",
        281836,  # ID factura
        body="<p>Test de mensaje</p>",
        message_type="comment",
        subtype_xmlid="mail.mt_note",
        attachment_ids=[(6, 0, [attachment_id])]
    )
    print(f"   Resultado: {post_result}")
    print(f"   Tipo: {type(post_result)}")
    
    if post_result is None:
        print(f"   ⚠️ message_post retornó None (pero puede ser normal)")
    else:
        print(f"   ✅ Mensaje posteado")
    
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
print("✅ Test completado")
print("=" * 70)
