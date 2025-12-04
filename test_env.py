import os
from dotenv import load_dotenv
from pathlib import Path

# Probar cargar .env
load_dotenv()
load_dotenv(Path(__file__).parent / ".env")

print("URL:", os.getenv("ODOO_URL"))
print("DB:", os.getenv("ODOO_DB"))
print("USER:", os.getenv("ODOO_USER"))
print("PASS:", os.getenv("ODOO_PASSWORD")[:15] if os.getenv("ODOO_PASSWORD") else None)

# Probar conexión
import xmlrpc.client
url = os.getenv("ODOO_URL")
db = os.getenv("ODOO_DB")
user = os.getenv("ODOO_USER")
pwd = os.getenv("ODOO_PASSWORD")

print("\nProbando conexión XML-RPC...")
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
try:
    uid = common.authenticate(db, user, pwd, {})
    print("UID:", uid)
    if uid:
        print("✅ Conexión exitosa!")
    else:
        print("❌ Autenticación fallida - UID es None o False")
except Exception as e:
    print("❌ Error:", e)
