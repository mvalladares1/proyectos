"""
Script para gestionar módulos en Odoo
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from shared.odoo_client import OdooClient

# Credenciales
ODOO_URL = "https://riofuturo.server98c6e.oerpondemand.net"
ODOO_DB = "riofuturo-master"
ODOO_USER = "mvalladares@riofuturo.cl"
ODOO_PASSWORD = "c0766224bec30cac071ffe43a858c9ccbd521ddd"


def list_modules():
    """Listar módulos relacionados con logs y transferencia/dashboard"""
    client = OdooClient(
        username=ODOO_USER,
        password=ODOO_PASSWORD,
        url=ODOO_URL,
        db=ODOO_DB
    )
    
    print("=" * 70)
    print("📦 MÓDULOS INSTALADOS - LOGS")
    print("=" * 70)
    
    # Buscar módulos con "log" en el nombre
    log_modules = client.search_read(
        'ir.module.module',
        [['name', 'ilike', 'log']],
        ['id', 'name', 'shortdesc', 'state', 'installed_version']
    )
    
    for m in log_modules:
        print(f"\n  ID: {m['id']}")
        print(f"  Nombre técnico: {m['name']}")
        print(f"  Descripción: {m['shortdesc']}")
        print(f"  Estado: {m['state']}")
        print(f"  Versión: {m['installed_version']}")
    
    print("\n" + "=" * 70)
    print("📦 MÓDULOS INSTALADOS - TRANSFERENCIA / DASHBOARD")
    print("=" * 70)
    
    # Buscar módulos con "transfer" o "dashboard" en el nombre
    transfer_modules = client.search_read(
        'ir.module.module',
        ['|', ['name', 'ilike', 'transfer'], ['name', 'ilike', 'dashboard']],
        ['id', 'name', 'shortdesc', 'state', 'installed_version']
    )
    
    for m in transfer_modules:
        # Solo mostrar los instalados o a instalar
        if m['state'] in ['installed', 'to install', 'to upgrade']:
            print(f"\n  ID: {m['id']}")
            print(f"  Nombre técnico: {m['name']}")
            print(f"  Descripción: {m['shortdesc']}")
            print(f"  Estado: {m['state']}")
            print(f"  Versión: {m['installed_version']}")
    
    print("\n" + "=" * 70)
    print("📦 TODOS LOS MÓDULOS PERSONALIZADOS (no base)")
    print("=" * 70)
    
    # Buscar módulos custom (no de Odoo base)
    custom_modules = client.search_read(
        'ir.module.module',
        [
            ['state', 'in', ['installed', 'to install', 'to upgrade']],
            ['author', 'not ilike', 'Odoo S.A.'],
            ['author', 'not ilike', 'Odoo SA'],
            ['author', '!=', False]
        ],
        ['id', 'name', 'shortdesc', 'state', 'author', 'installed_version'],
        limit=50
    )
    
    for m in custom_modules:
        print(f"\n  ID: {m['id']}")
        print(f"  Nombre: {m['name']} - {m['shortdesc']}")
        print(f"  Autor: {m['author']}")
        print(f"  Estado: {m['state']}")


if __name__ == "__main__":
    list_modules()
