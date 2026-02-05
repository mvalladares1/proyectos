"""
Debug: Revisar configuración de correo en Odoo
"""
import xmlrpc.client

# Credenciales (API Key)
URL = "https://riofuturo.server98c6e.oerpondemand.net"
DB = "riofuturo-master"
USERNAME = "mvalladares@riofuturo.cl"
PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"

# Conectar
common = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/common')
uid = common.authenticate(DB, USERNAME, PASSWORD, {})
models = xmlrpc.client.ServerProxy(f'{URL}/xmlrpc/2/object')

print("=" * 70)
print("📧 CONFIGURACIÓN DE CORREO EN ODOO")
print("=" * 70)

# 1. Servidores de correo saliente
print("\n1️⃣ SERVIDORES DE CORREO SALIENTE (ir.mail_server)")
print("-" * 50)

mail_servers = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.mail_server', 'search_read',
    [[]],
    {'fields': ['name', 'smtp_host', 'smtp_port', 'smtp_user', 'smtp_encryption', 'active', 'sequence']}
)

if mail_servers:
    for server in mail_servers:
        print(f"\n   📤 {server['name']}")
        print(f"      Host: {server['smtp_host']}:{server['smtp_port']}")
        print(f"      Usuario: {server['smtp_user']}")
        print(f"      Encriptación: {server['smtp_encryption']}")
        print(f"      Activo: {'✅' if server['active'] else '❌'}")
        print(f"      Secuencia: {server['sequence']}")
else:
    print("   ⚠️ No hay servidores de correo saliente configurados")

# 2. Parámetros del sistema relacionados con email
print("\n\n2️⃣ PARÁMETROS DEL SISTEMA (mail)")
print("-" * 50)

params_mail = models.execute_kw(
    DB, uid, PASSWORD,
    'ir.config_parameter', 'search_read',
    [[('key', 'ilike', 'mail')]],
    {'fields': ['key', 'value']}
)

for param in params_mail:
    print(f"   {param['key']}: {param['value']}")

# 3. Configuración de la compañía (email)
print("\n\n3️⃣ CONFIGURACIÓN DE LA COMPAÑÍA")
print("-" * 50)

companies = models.execute_kw(
    DB, uid, PASSWORD,
    'res.company', 'search_read',
    [[]],
    {'fields': ['name', 'email', 'partner_id'], 'limit': 5}
)

for company in companies:
    print(f"\n   🏢 {company['name']}")
    print(f"      Email: {company.get('email', 'No configurado')}")
    
    # Obtener email del partner de la compañía
    if company.get('partner_id'):
        partner = models.execute_kw(
            DB, uid, PASSWORD,
            'res.partner', 'read',
            [company['partner_id'][0]],
            {'fields': ['email']}
        )
        if partner:
            print(f"      Email Partner: {partner[0].get('email', 'No configurado')}")

# 4. Templates de correo existentes para facturas
print("\n\n4️⃣ PLANTILLAS DE CORREO PARA FACTURAS")
print("-" * 50)

templates = models.execute_kw(
    DB, uid, PASSWORD,
    'mail.template', 'search_read',
    [[('model', '=', 'account.move')]],
    {'fields': ['name', 'email_from', 'email_to', 'subject', 'use_default_to'], 'limit': 10}
)

if templates:
    for tpl in templates:
        print(f"\n   📄 {tpl['name']}")
        print(f"      Desde: {tpl.get('email_from', 'Default')}")
        print(f"      Para: {tpl.get('email_to', 'Default')}")
        print(f"      Asunto: {tpl.get('subject', 'Sin asunto')[:50]}")
else:
    print("   No hay plantillas de correo para account.move")

# 5. Alias de correo
print("\n\n5️⃣ ALIAS DE CORREO (mail.alias)")
print("-" * 50)

aliases = models.execute_kw(
    DB, uid, PASSWORD,
    'mail.alias', 'search_read',
    [[('alias_model_id', '!=', False)]],
    {'fields': ['alias_name', 'alias_domain', 'alias_model_id'], 'limit': 10}
)

for alias in aliases[:5]:
    model_name = alias.get('alias_model_id', [None, 'Desconocido'])
    print(f"   {alias.get('alias_name', 'Sin nombre')}@{alias.get('alias_domain', '')} → {model_name[1] if isinstance(model_name, list) else model_name}")

# 6. Últimos correos enviados
print("\n\n6️⃣ ÚLTIMOS CORREOS ENVIADOS (mail.mail)")
print("-" * 50)

mails = models.execute_kw(
    DB, uid, PASSWORD,
    'mail.mail', 'search_read',
    [[('state', '=', 'sent')]],
    {'fields': ['subject', 'email_from', 'email_to', 'create_date', 'state'], 
     'limit': 5, 
     'order': 'create_date desc'}
)

if mails:
    for mail in mails:
        print(f"\n   📨 {mail.get('subject', 'Sin asunto')[:40]}")
        print(f"      Desde: {mail.get('email_from', 'N/A')}")
        print(f"      Para: {mail.get('email_to', 'N/A')}")
        print(f"      Fecha: {mail.get('create_date', 'N/A')}")
        print(f"      Estado: {mail.get('state', 'N/A')}")
else:
    print("   No hay correos enviados recientes")

print("\n" + "=" * 70)
print("✅ Diagnóstico completado")
print("=" * 70)
