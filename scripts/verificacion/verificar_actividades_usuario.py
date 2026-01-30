#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar qué actividades/aprobaciones ve cada usuario
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from shared.odoo_client import OdooClient

def main():
    # Conectar con el usuario actual (debería ser MAXIMO)
    odoo = OdooClient(
        username='mvalladares@riofuturo.cl',
        password='c0766224bec30cac071ffe43a858c9ccbd521ddd'
    )
    
    print("\n" + "="*80)
    print("VERIFICANDO ACTIVIDADES VISIBLES PARA EL USUARIO ACTUAL")
    print("="*80)
    
    # Obtener info del usuario actual
    uid = odoo.uid
    user_info = odoo.search_read('res.users', [('id', '=', uid)], ['name', 'login'])
    print(f"\nUsuario conectado: {user_info[0]['name']} ({user_info[0]['login']})")
    print(f"UID: {uid}")
    
    # Buscar actividades asignadas al usuario actual
    print("\n" + "="*80)
    print("ACTIVIDADES ASIGNADAS AL USUARIO ACTUAL")
    print("="*80)
    
    actividades_usuario = odoo.search_read(
        'mail.activity',
        [('user_id', '=', uid)],
        ['summary', 'res_model', 'res_id', 'res_name', 'activity_type_id', 'date_deadline'],
        limit=50
    )
    
    print(f"\nActividades asignadas a ti: {len(actividades_usuario)}")
    
    if actividades_usuario:
        print("\nDetalle de actividades:")
        for act in actividades_usuario:
            print(f"\n  Modelo: {act.get('res_model')}")
            print(f"  Registro: {act.get('res_name')} (ID: {act.get('res_id')})")
            print(f"  Tipo: {act.get('activity_type_id')}")
            print(f"  Resumen: {act.get('summary')}")
            print(f"  Fecha límite: {act.get('date_deadline')}")
    
    # Buscar TODAS las actividades (sin filtro de usuario)
    print("\n" + "="*80)
    print("TODAS LAS ACTIVIDADES EN EL SISTEMA")
    print("="*80)
    
    todas_actividades = odoo.search_read(
        'mail.activity',
        [],
        ['summary', 'res_model', 'res_id', 'user_id', 'activity_type_id'],
        limit=100
    )
    
    print(f"\nTotal actividades en el sistema: {len(todas_actividades)}")
    
    # Agrupar por usuario asignado
    actividades_por_usuario = {}
    for act in todas_actividades:
        user_id = act.get('user_id')
        if user_id:
            user_id_int = user_id[0] if isinstance(user_id, (list, tuple)) else user_id
            if user_id_int not in actividades_por_usuario:
                actividades_por_usuario[user_id_int] = 0
            actividades_por_usuario[user_id_int] += 1
    
    print("\nActividades por usuario:")
    for user_id, count in sorted(actividades_por_usuario.items(), key=lambda x: x[1], reverse=True):
        user = odoo.search_read('res.users', [('id', '=', user_id)], ['name'])
        if user:
            print(f"  {user[0]['name']} (ID: {user_id}): {count} actividades")
    
    # Verificar reglas de acceso para mail.activity
    print("\n" + "="*80)
    print("REGLAS DE REGISTRO PARA mail.activity")
    print("="*80)
    
    try:
        reglas = odoo.search_read(
            'ir.rule',
            [('model_id.model', '=', 'mail.activity')],
            ['name', 'domain_force', 'groups']
        )
        
        if reglas:
            print(f"\nReglas encontradas: {len(reglas)}\n")
            for regla in reglas:
                print(f"Regla: {regla.get('name')}")
                print(f"  Dominio: {regla.get('domain_force')}")
                print(f"  Grupos: {regla.get('groups')}")
                print()
        else:
            print("\n❌ No se encontraron reglas de registro para mail.activity")
            print("   Esto significa que TODOS los usuarios ven TODAS las actividades")
    except Exception as e:
        print(f"Error al buscar reglas: {e}")
    
    # Verificar grupos del usuario actual
    print("\n" + "="*80)
    print("GRUPOS DEL USUARIO ACTUAL")
    print("="*80)
    
    user_full = odoo.search_read('res.users', [('id', '=', uid)], ['groups_id'])
    if user_full and user_full[0].get('groups_id'):
        group_ids = user_full[0]['groups_id']
        grupos = odoo.search_read('res.groups', [('id', 'in', group_ids)], ['name', 'full_name'])
        
        print(f"\nGrupos del usuario ({len(grupos)}):")
        for grupo in grupos:
            print(f"  - {grupo.get('full_name') or grupo.get('name')}")

if __name__ == "__main__":
    main()
