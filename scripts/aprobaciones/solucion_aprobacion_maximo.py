#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Verificar campo Categoría en OCs y configurar aprobación solo para MAXIMO
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient

def main():
    odoo = OdooClient(
        url='https://riofuturo.server98c6e.oerpondemand.net',
        db='riofuturo-master',
        username='mvalladares@riofuturo.cl',
        password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
    )
    
    maximo_id = 241
    
    print("\n" + "="*80)
    print("ANÁLISIS CAMPO CATEGORÍA Y SOLUCIÓN PARA TRANSPORTES + SERVICIOS")
    print("="*80)
    
    # 1. Buscar definición del campo x_studio_categora
    print("\n1. DEFINICIÓN DEL CAMPO CATEGORÍA:")
    print("-" * 80)
    
    campo = odoo.search_read(
        'ir.model.fields',
        [('model', '=', 'purchase.order'), ('name', '=', 'x_studio_categora')],
        ['name', 'field_description', 'ttype', 'selection']
    )
    
    if campo:
        print(f"  Campo: {campo[0]['field_description']}")
        print(f"  Nombre técnico: {campo[0]['name']}")
        print(f"  Tipo: {campo[0]['ttype']}")
        if campo[0].get('selection'):
            print(f"  Valores posibles: {campo[0]['selection']}")
    
    # 2. Ver valores de categoría en OCs recientes
    print("\n2. OCS CON CATEGORÍAS DEFINIDAS:")
    print("-" * 80)
    
    ocs = odoo.search_read(
        'purchase.order',
        [('x_studio_categora', '!=', False)],
        ['name', 'x_studio_categora', 'state', 'partner_id'],
        limit=20
    )
    
    categorias_encontradas = {}
    for oc in ocs:
        cat = oc.get('x_studio_categora')
        if cat:
            if cat not in categorias_encontradas:
                categorias_encontradas[cat] = []
            categorias_encontradas[cat].append(oc['name'])
    
    print(f"\n  Categorías encontradas en OCs:")
    for cat, ocs_list in categorias_encontradas.items():
        print(f"    - {cat}: {len(ocs_list)} OCs")
        print(f"      Ejemplos: {', '.join(ocs_list[:3])}")
    
    # 3. Ver OC12312 específicamente
    print("\n3. OC12312 - CATEGORÍA Y APROBADORES:")
    print("-" * 80)
    
    oc12312 = odoo.search_read(
        'purchase.order',
        [('name', '=', 'OC12312')],
        ['name', 'x_studio_categora', 'x_studio_categora_de_producto', 
         'state', 'partner_id', 'amount_total']
    )
    
    if oc12312:
        print(f"  OC: {oc12312[0]['name']}")
        print(f"  Categoría: {oc12312[0].get('x_studio_categora')}")
        print(f"  Categoría de Producto: {oc12312[0].get('x_studio_categora_de_producto')}")
        print(f"  Estado: {oc12312[0]['state']}")
        print(f"  Proveedor: {oc12312[0]['partner_id']}")
        
        # Ver actividades
        actividades = odoo.search_read(
            'mail.activity',
            [('res_model', '=', 'purchase.order'), ('res_id', '=', oc12312[0]['id'])],
            ['user_id', 'summary', 'activity_type_id']
        )
        
        print(f"\n  Aprobadores asignados: {len(actividades)}")
        for act in actividades:
            user = act['user_id']
            user_id = user[0] if isinstance(user, (list, tuple)) else user
            user_name = user[1] if isinstance(user, (list, tuple)) else user
            simbolo = "✓" if user_id == maximo_id else "✗"
            print(f"    {simbolo} {user_name} (ID: {user_id})")
    
    # 4. Buscar automatizaciones que crean actividades con categoría TRANSPORTES + SERVICIOS
    print("\n4. BUSCANDO AUTOMATIZACIONES QUE ASIGNAN APROBADORES:")
    print("-" * 80)
    
    all_automations = odoo.search_read(
        'base.automation',
        [('model_id.model', '=', 'purchase.order')],
        ['id', 'name', 'trigger', 'filter_domain', 'active']
    )
    
    print(f"  Total automatizaciones en purchase.order: {len(all_automations)}")
    for auto in all_automations:
        print(f"\n    - {auto['name']} (ID: {auto['id']})")
        print(f"      Trigger: {auto.get('trigger')}")
        print(f"      Activa: {auto.get('active')}")
        if auto.get('filter_domain'):
            print(f"      Dominio: {auto['filter_domain']}")
    
    # 5. Buscar acciones de servidor que crean mail.activity
    print("\n5. ACCIONES QUE CREAN ACTIVIDADES DE APROBACIÓN:")
    print("-" * 80)
    
    actions = odoo.search_read(
        'ir.actions.server',
        [('state', '=', 'code')],
        ['id', 'name', 'model_id', 'code'],
        limit=50
    )
    
    acciones_actividad = []
    for action in actions:
        if action.get('code') and 'mail.activity' in action['code']:
            acciones_actividad.append(action)
    
    print(f"  Acciones que crean actividades: {len(acciones_actividad)}")
    for action in acciones_actividad[:10]:
        print(f"\n    Acción: {action['name']} (ID: {action['id']})")
        print(f"    Modelo: {action.get('model_id')}")
        
        # Verificar si menciona categoría o transportes/servicios
        code = action.get('code', '')
        if 'categor' in code.lower() or 'servic' in code.lower() or 'transport' in code.lower():
            print(f"    ⚠️  Código relacionado con categoría/servicios:")
            lines = code.split('\n')
            for i, line in enumerate(lines):
                if any(keyword in line.lower() for keyword in ['categor', 'servic', 'transport', 'maximo', 'user_id']):
                    print(f"      L{i+1}: {line}")
    
    # 6. Solución propuesta
    print("\n\n" + "="*80)
    print("SOLUCIÓN PROPUESTA")
    print("="*80)
    print(f"""
Para que SOLO MAXIMO apruebe las OCs de "TRANSPORTES + SERVICIOS":

Opción 1: MODIFICAR AUTOMATIZACIÓN EXISTENTE
  - Buscar la automatización que asigna aprobadores según categoría
  - Modificar el código Python para que cuando x_studio_categora == "TRANSPORTES + SERVICIOS"
    solo se cree 1 actividad asignada a MAXIMO (ID: {maximo_id})

Opción 2: CREAR NUEVA AUTOMATIZACIÓN
  - Nombre: "Aprobación MAXIMO - Transportes + Servicios"
  - Trigger: on_write
  - Dominio: [('x_studio_categora', '=', 'TRANSPORTES + SERVICIOS'), ('state', '=', 'sent')]
  - Acción: Eliminar otras actividades y crear solo 1 para MAXIMO

Opción 3: REGLA DE REGISTRO (ir.rule)
  - Crear regla que filtre mail.activity para que Miguel solo vea las de MAXIMO
  - Dominio: [('user_id', '=', {maximo_id})] cuando res_model='purchase.order' y OC es de Servicios

¿Cuál prefieres que implemente?
    """)

if __name__ == "__main__":
    main()
