#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Crear automatización para que SOLO MAXIMO apruebe OCs de Transportes + Servicios
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
    print("BUSCAR DÓNDE SE CREAN LAS ACTIVIDADES DE APROBACIÓN")
    print("="*80)
    
    # 1. Buscar TODAS las automatizaciones activas
    print("\n1. TODAS LAS AUTOMATIZACIONES ACTIVAS:")
    print("-" * 80)
    
    all_automations = odoo.search_read(
        'base.automation',
        [('active', '=', True)],
        ['id', 'name', 'model_id', 'trigger', 'filter_domain']
    )
    
    print(f"  Total automatizaciones activas: {len(all_automations)}\n")
    
    # Filtrar las relacionadas con purchase.order
    po_automations = [a for a in all_automations 
                     if a.get('model_id') and 'purchase.order' in str(a['model_id'])]
    
    print(f"  Automatizaciones en purchase.order: {len(po_automations)}")
    for auto in po_automations:
        print(f"    - {auto['name']} (ID: {auto['id']})")
    
    # 2. Buscar acciones de servidor ejecutadas por automatizaciones
    print("\n2. ACCIONES DE SERVIDOR EN AUTOMATIZACIONES:")
    print("-" * 80)
    
    automation_actions = odoo.search_read(
        'base.automation',
        [('model_id.model', '=', 'purchase.order'), ('active', '=', True)],
        ['id', 'name', 'action_server_id', 'child_ids']
    )
    
    for auto in automation_actions:
        print(f"\n  Automatización: {auto['name']} (ID: {auto['id']})")
        
        if auto.get('action_server_id'):
            action_id = auto['action_server_id'][0]
            print(f"    Acción principal: {auto['action_server_id'][1]} (ID: {action_id})")
            
            # Obtener código de la acción
            action_detail = odoo.search_read(
                'ir.actions.server',
                [('id', '=', action_id)],
                ['name', 'state', 'code', 'child_ids']
            )
            
            if action_detail and action_detail[0].get('code'):
                print(f"    Código:")
                code_lines = action_detail[0]['code'].split('\n')
                for line in code_lines[:50]:
                    if line.strip():
                        print(f"      {line}")
                if len(code_lines) > 50:
                    print(f"      ... ({len(code_lines) - 50} líneas más)")
            
            # Ver acciones hijas
            if action_detail and action_detail[0].get('child_ids'):
                print(f"\n    Acciones hijas: {action_detail[0]['child_ids']}")
                
                child_actions = odoo.search_read(
                    'ir.actions.server',
                    [('id', 'in', action_detail[0]['child_ids'])],
                    ['id', 'name', 'code']
                )
                
                for child in child_actions:
                    print(f"\n      - {child['name']} (ID: {child['id']})")
                    if child.get('code'):
                        child_lines = child['code'].split('\n')
                        for line in child_lines[:30]:
                            if line.strip():
                                print(f"        {line}")
                        if len(child_lines) > 30:
                            print(f"        ... ({len(child_lines) - 30} líneas más)")
    
    # 3. Buscar en métodos personalizados del modelo purchase.order
    print("\n\n3. BUSCANDO MÉTODOS PERSONALIZADOS:")
    print("-" * 80)
    
    # Ver si hay campo computado o trigger que crea actividades
    campos_computados = odoo.search_read(
        'ir.model.fields',
        [('model', '=', 'purchase.order'), ('compute', '!=', False)],
        ['name', 'field_description', 'compute']
    )
    
    if campos_computados:
        print(f"  Campos computados en purchase.order: {len(campos_computados)}")
        for campo in campos_computados[:10]:
            print(f"    - {campo['field_description']} ({campo['name']})")
            print(f"      Compute: {campo.get('compute')}")
    
    print("\n\n" + "="*80)
    print("RECOMENDACIÓN FINAL")
    print("="*80)
    print(f"""
Basado en el análisis:

1. Las OCs de SERVICIOS usan el campo: x_studio_categora_de_producto = "SERVICIOS"
2. Actualmente se asignan 4 aprobadores por alguna lógica oculta
3. MAXIMO (ID: {maximo_id}) debe ser el ÚNICO aprobador

SOLUCIÓN MÁS DIRECTA:
Necesito acceder a Odoo como administrador para:

A) IDENTIFICAR: ¿Dónde se crean esas 4 actividades?
   - Puede ser en el código del módulo purchase
   - Puede ser en un workflow oculto
   - Puede ser en la lógica de confirmación de OC

B) CONFIGURAR: 
   - Si hay módulo de aprobaciones instalado (approval, purchase_approval)
   - Configurar regla: Categoría SERVICIOS → Solo MAXIMO aprueba
   
C) ALTERNATIVA RÁPIDA desde Python:
   - Crear script que al confirmar OC de SERVICIOS:
     * Elimine todas las actividades de aprobación
     * Cree solo 1 actividad asignada a MAXIMO

¿Quieres que cree el script de Python que limpie y asigne solo a MAXIMO?
O ¿tienes acceso admin a Odoo para revisar la configuración de aprobaciones?
    """)

if __name__ == "__main__":
    main()
