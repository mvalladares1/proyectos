"""
Investigar los menús de Trasferencias Dashboard
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


def investigate_menus():
    """Investigar los menús de Trasferencias Dashboard"""
    client = OdooClient(
        username=ODOO_USER,
        password=ODOO_PASSWORD,
        url=ODOO_URL,
        db=ODOO_DB
    )
    
    menu_ids = [993, 995, 997, 996]  # Los 3 Trasferencias + Logs
    
    for menu_id in menu_ids:
        print(f"\n{'='*70}")
        print(f"📋 MENÚ ID: {menu_id}")
        print(f"{'='*70}")
        
        # Info del menú
        menu = client.search_read(
            'ir.ui.menu',
            [['id', '=', menu_id]],
            ['id', 'name', 'complete_name', 'action', 'child_id', 'parent_id', 'sequence', 'web_icon']
        )
        
        if not menu:
            print(f"   ❌ No encontrado")
            continue
        
        menu = menu[0]
        print(f"   Nombre: {menu['name']}")
        print(f"   Ruta: {menu.get('complete_name')}")
        print(f"   Parent: {menu.get('parent_id')}")
        print(f"   Sequence: {menu.get('sequence')}")
        print(f"   Icon: {menu.get('web_icon', '-')}")
        print(f"   Hijos: {menu.get('child_id')}")
        
        # Si tiene action, investigarla
        action_ref = menu.get('action')
        if action_ref:
            action_type, action_id = action_ref.split(',')
            action_id = int(action_id)
            
            print(f"\n   🎯 ACTION: {action_type} ID={action_id}")
            
            if action_type == 'ir.actions.act_window':
                action = client.search_read(
                    'ir.actions.act_window',
                    [['id', '=', action_id]],
                    ['id', 'name', 'res_model', 'view_mode', 'domain', 'context', 'search_view_id']
                )
                
                if action:
                    action = action[0]
                    print(f"      Nombre: {action['name']}")
                    print(f"      Modelo: {action['res_model']}")
                    print(f"      Vistas: {action['view_mode']}")
                    print(f"      Domain: {action.get('domain')}")
                    
                    # Contar registros del modelo
                    try:
                        count = client.models.execute_kw(
                            client.db, client.uid, client.password,
                            action['res_model'], 'search_count', [[]]
                        )
                        print(f"      📊 Total registros: {count}")
                        
                        # Ver últimos 3 registros
                        if count > 0:
                            latest = client.search_read(
                                action['res_model'],
                                [],
                                ['id', 'name', 'create_date', 'write_date'],
                                limit=3,
                                order='write_date desc'
                            )
                            print(f"      📝 Últimos registros:")
                            for r in latest:
                                print(f"         - [{r['id']}] {r.get('name', '-')} | Modificado: {r.get('write_date', '-')}")
                    except Exception as e:
                        print(f"      ⚠️ Error contando: {e}")
        
        # Ver submenús
        if menu.get('child_id'):
            print(f"\n   📁 SUBMENÚS:")
            submenus = client.search_read(
                'ir.ui.menu',
                [['id', 'in', menu['child_id']]],
                ['id', 'name', 'action']
            )
            for sub in submenus:
                print(f"      - [{sub['id']}] {sub['name']} | Action: {sub.get('action')}")


if __name__ == "__main__":
    investigate_menus()
