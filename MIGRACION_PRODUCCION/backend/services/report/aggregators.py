"""
Funciones de agregación de datos de recepciones.
"""
from typing import List, Dict, Any


def normalize_categoria(cat: str) -> str:
    """Normaliza nombres de categorías."""
    if not cat:
        return ''
    c = cat.strip().upper()
    if 'BANDEJ' in c:
        return 'BANDEJAS'
    return c


def aggregate_envases(recepciones: List[Dict[str, Any]]) -> Dict[str, float]:
    """Agrupa envases (bandejas) por nombre de producto para desglose detallado."""
    envases = {}
    for r in recepciones:
        for p in r.get('productos', []) or []:
            categoria = normalize_categoria(p.get('Categoria', ''))
            if categoria == 'BANDEJAS':
                nombre = p.get('Producto', 'Sin nombre')
                envases[nombre] = envases.get(nombre, 0) + (p.get('Kg Hechos', 0) or 0)
    return envases


def aggregate_by_fruta(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Agrupa recepciones por tipo_fruta y calcula métricas por fruta."""
    agrup = {}
    for r in recepciones:
        # Excluir productor ADMINISTRADOR
        productor = (r.get('productor') or '').strip()
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
        tipo = (r.get('tipo_fruta') or '').strip()
        if not tipo:
            continue
        if tipo not in agrup:
            agrup[tipo] = {
                'kg': 0.0,
                'costo': 0.0,
                'iqf_vals': [],
                'block_vals': [],
                'n_recepciones': 0,
                'productores': {}
            }
        entry = agrup[tipo]
        entry['n_recepciones'] += 1
        # recorrer productos para sumar kg y costo excluyendo bandejas
        for p in r.get('productos', []) or []:
            cat = normalize_categoria(p.get('Categoria', ''))
            kg = p.get('Kg Hechos', 0) or 0
            costo = p.get('Costo Total', 0) or 0
            if cat == 'BANDEJAS':
                # skip bandejas from kg/costo of fruit
                continue
            entry['kg'] += kg
            entry['costo'] += costo
        # quality averages
        entry['iqf_vals'].append(r.get('total_iqf', 0) or 0)
        entry['block_vals'].append(r.get('total_block', 0) or 0)
        # productores
        prod = r.get('productor') or ''
        if prod:
            entry['productores'][prod] = entry['productores'].get(prod, 0) + (r.get('kg_recepcionados') or 0)

    # convertir a lista con cálculos
    out = []
    for tipo, v in agrup.items():
        kg = v['kg']
        costo = v['costo']
        costo_prom = (costo / kg) if kg > 0 else None
        prom_iqf = (sum(v['iqf_vals']) / len(v['iqf_vals'])) if v['iqf_vals'] else 0
        prom_block = (sum(v['block_vals']) / len(v['block_vals'])) if v['block_vals'] else 0
        top_productores = sorted(v['productores'].items(), key=lambda x: x[1], reverse=True)[:5]
        out.append({
            'tipo_fruta': tipo,
            'kg': kg,
            'costo': costo,
            'costo_prom': costo_prom,
            'prom_iqf': prom_iqf,
            'prom_block': prom_block,
            'n_recepciones': v['n_recepciones'],
            'top_productores': top_productores
        })
    # orden por Kg descendente
    out.sort(key=lambda x: x['kg'], reverse=True)
    return out


def aggregate_by_fruta_manejo(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa recepciones por tipo_fruta (del producto) y luego por manejo.
    Retorna estructura jerárquica para mostrar en tablas.
    """
    # Estructura: {tipo_fruta: {manejo: {kg, costo, iqf_vals, block_vals}}}
    agrup = {}
    
    for r in recepciones:
        # Excluir productor ADMINISTRADOR
        productor = (r.get('productor') or '').strip()
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
        # Tipo de fruta del QC (para asociar IQF/Block)
        tipo_fruta_qc = (r.get('tipo_fruta') or '').strip()
        
        # IQF/Block son a nivel de recepción
        iqf_val = r.get('total_iqf', 0) or 0
        block_val = r.get('total_block', 0) or 0
        
        # Rastrear manejos por cada tipo de fruta
        manejos_por_tipo = {}
        
        # Recorrer productos para obtener tipo y manejo del producto
        for p in r.get('productos', []) or []:
            cat = normalize_categoria(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue  # Excluir bandejas
            
            kg = p.get('Kg Hechos', 0) or 0
            if kg <= 0:
                continue  # Ignorar productos con 0 kg
            
            # Usar TipoFruta del producto, con fallback al tipo_fruta del QC
            tipo = (p.get('TipoFruta') or tipo_fruta_qc or '').strip()
            if not tipo:
                continue
            
            manejo = (p.get('Manejo') or '').strip()
            if not manejo:
                manejo = 'Sin Manejo'
            
            # Rastrear manejos por tipo
            if tipo not in manejos_por_tipo:
                manejos_por_tipo[tipo] = set()
            manejos_por_tipo[tipo].add(manejo)
            
            if tipo not in agrup:
                agrup[tipo] = {}
            
            if manejo not in agrup[tipo]:
                agrup[tipo][manejo] = {
                    'kg': 0.0,
                    'costo': 0.0,
                    'iqf_vals': [],
                    'block_vals': []
                }
            
            costo = p.get('Costo Total', 0) or 0
            agrup[tipo][manejo]['kg'] += kg
            agrup[tipo][manejo]['costo'] += costo
        
        # Agregar IQF/Block SOLO al tipo de fruta del QC
        # (no a todos los productos, ya que IQF/Block son mediciones del tipo_fruta del QC)
        if tipo_fruta_qc and tipo_fruta_qc in manejos_por_tipo:
            for manejo in manejos_por_tipo[tipo_fruta_qc]:
                if tipo_fruta_qc in agrup and manejo in agrup[tipo_fruta_qc]:
                    agrup[tipo_fruta_qc][manejo]['iqf_vals'].append(iqf_val)
                    agrup[tipo_fruta_qc][manejo]['block_vals'].append(block_val)

    
    # Convertir a lista jerárquica
    out = []
    for tipo, manejos in agrup.items():
        tipo_kg = sum(m['kg'] for m in manejos.values())
        
        # Omitir tipos de fruta sin kg
        if tipo_kg <= 0:
            continue
            
        tipo_costo = sum(m['costo'] for m in manejos.values())
        
        manejo_list = []
        for manejo, v in sorted(manejos.items()):
            kg = v['kg']
            # Omitir manejos sin kg
            if kg <= 0:
                continue
                
            costo = v['costo']
            costo_prom = (costo / kg) if kg > 0 else None
            prom_iqf = (sum(v['iqf_vals']) / len(v['iqf_vals'])) if v['iqf_vals'] else 0
            prom_block = (sum(v['block_vals']) / len(v['block_vals'])) if v['block_vals'] else 0
            
            manejo_list.append({
                'manejo': manejo,
                'kg': kg,
                'costo': costo,
                'costo_prom': costo_prom,
                'prom_iqf': prom_iqf,
                'prom_block': prom_block
            })
        
        # Omitir tipos sin manejos válidos
        if not manejo_list:
            continue
        
        # Ordenar manejos por kg descendente
        manejo_list.sort(key=lambda x: x['kg'], reverse=True)
        
        out.append({
            'tipo_fruta': tipo,
            'kg_total': tipo_kg,
            'costo_total': tipo_costo,
            'manejos': manejo_list
        })
    
    # Ordenar tipos por kg descendente
    out.sort(key=lambda x: x['kg_total'], reverse=True)
    return out


def aggregate_by_fruta_productor_manejo(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa recepciones por Tipo de Fruta → Productor → Manejo.
    Para cada nivel calcula: Kg, Costo Total, Costo Promedio/Kg.
    """
    # Estructura: {tipo_fruta: {productor: {manejo: {kg, costo}}}}
    agrup = {}
    
    for r in recepciones:
        tipo_fruta_qc = (r.get('tipo_fruta') or '').strip()
        
        productor = (r.get('productor') or '').strip()
        if not productor:
            productor = 'Sin Productor'
        
        # Excluir productor ADMINISTRADOR
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
        # Recorrer productos para obtener tipo, manejo y sumar kg/costo
        for p in r.get('productos', []) or []:
            cat = normalize_categoria(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue  # Excluir bandejas
            
            kg = p.get('Kg Hechos', 0) or 0
            if kg <= 0:
                continue  # Ignorar productos con 0 kg
            
            # Usar TipoFruta del producto, con fallback al tipo_fruta del QC
            tipo_fruta = (p.get('TipoFruta') or tipo_fruta_qc or '').strip()
            if not tipo_fruta:
                continue
            
            manejo = (p.get('Manejo') or '').strip()
            if not manejo:
                manejo = 'Sin Manejo'
            
            if tipo_fruta not in agrup:
                agrup[tipo_fruta] = {}
            
            if productor not in agrup[tipo_fruta]:
                agrup[tipo_fruta][productor] = {}
            
            if manejo not in agrup[tipo_fruta][productor]:
                agrup[tipo_fruta][productor][manejo] = {'kg': 0.0, 'costo': 0.0}
            
            costo = p.get('Costo Total', 0) or 0
            agrup[tipo_fruta][productor][manejo]['kg'] += kg
            agrup[tipo_fruta][productor][manejo]['costo'] += costo
    
    # Convertir a lista jerárquica
    out = []
    for tipo_fruta, productores in agrup.items():
        tipo_kg = 0.0
        tipo_costo = 0.0
        
        productores_list = []
        for productor, manejos in productores.items():
            productor_kg = sum(m['kg'] for m in manejos.values())
            
            # Omitir productores sin kg
            if productor_kg <= 0:
                continue
                
            productor_costo = sum(m['costo'] for m in manejos.values())
            productor_costo_prom = (productor_costo / productor_kg) if productor_kg > 0 else None
            
            tipo_kg += productor_kg
            tipo_costo += productor_costo
            
            manejos_list = []
            for manejo, v in manejos.items():
                kg = v['kg']
                # Omitir manejos sin kg
                if kg <= 0:
                    continue
                costo = v['costo']
                costo_prom = (costo / kg) if kg > 0 else None
                manejos_list.append({
                    'manejo': manejo,
                    'kg': kg,
                    'costo': costo,
                    'costo_prom': costo_prom
                })
            
            # Omitir productores sin manejos válidos
            if not manejos_list:
                continue
            
            # Ordenar manejos por kg descendente
            manejos_list.sort(key=lambda x: x['kg'], reverse=True)
            
            productores_list.append({
                'productor': productor,
                'kg': productor_kg,
                'costo': productor_costo,
                'costo_prom': productor_costo_prom,
                'manejos': manejos_list
            })
        
        # Omitir tipos sin productores válidos
        if not productores_list:
            continue
        
        # Ordenar productores por kg descendente
        productores_list.sort(key=lambda x: x['kg'], reverse=True)
        
        tipo_costo_prom = (tipo_costo / tipo_kg) if tipo_kg > 0 else None
        
        out.append({
            'tipo_fruta': tipo_fruta,
            'kg': tipo_kg,
            'costo': tipo_costo,
            'costo_prom': tipo_costo_prom,
            'productores': productores_list
        })
    
    # Ordenar tipos por kg descendente
    out.sort(key=lambda x: x['kg'], reverse=True)
    return out


def aggregate_by_manejo_especie_productor(recepciones: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Agrupa recepciones por Manejo → Especie (Tipo de Fruta) → Productor.
    Orden: Orgánico primero, luego Convencional.
    Para cada nivel calcula: Kg, Costo Total, Costo Promedio/Kg.
    """
    # Estructura: {manejo: {especie: {productor: {kg, costo}}}}
    agrup = {}
    
    for r in recepciones:
        tipo_fruta_qc = (r.get('tipo_fruta') or '').strip()
        
        productor = (r.get('productor') or '').strip()
        if not productor:
            productor = 'Sin Productor'
        
        # Excluir productor ADMINISTRADOR
        if productor.upper() == 'ADMINISTRADOR':
            continue
        
        # Recorrer productos para obtener tipo, manejo y sumar kg/costo
        for p in r.get('productos', []) or []:
            cat = normalize_categoria(p.get('Categoria', ''))
            if cat == 'BANDEJAS':
                continue  # Excluir bandejas
            
            kg = p.get('Kg Hechos', 0) or 0
            if kg <= 0:
                continue  # Ignorar productos con 0 kg
            
            # Usar TipoFruta del producto, con fallback al tipo_fruta del QC
            especie = (p.get('TipoFruta') or tipo_fruta_qc or '').strip()
            if not especie:
                continue
            
            manejo_raw = (p.get('Manejo') or '').strip()
            # Normalizar manejo a Orgánico o Convencional
            if 'org' in manejo_raw.lower():
                manejo = 'Orgánico'
            elif manejo_raw:
                manejo = 'Convencional'
            else:
                manejo = 'Sin Manejo'
            
            if manejo not in agrup:
                agrup[manejo] = {}
            
            if especie not in agrup[manejo]:
                agrup[manejo][especie] = {}
            
            if productor not in agrup[manejo][especie]:
                agrup[manejo][especie][productor] = {'kg': 0.0, 'costo': 0.0}
            
            costo = p.get('Costo Total', 0) or 0
            agrup[manejo][especie][productor]['kg'] += kg
            agrup[manejo][especie][productor]['costo'] += costo
    
    # Convertir a lista jerárquica
    out = []
    
    # Orden de manejos: Orgánico primero, luego Convencional, luego otros
    manejo_order = ['Orgánico', 'Convencional']
    manejos_sorted = sorted(agrup.keys(), key=lambda x: (manejo_order.index(x) if x in manejo_order else 99, x))
    
    for manejo in manejos_sorted:
        especies = agrup[manejo]
        manejo_kg = 0.0
        manejo_costo = 0.0
        
        especies_list = []
        for especie, productores in especies.items():
            especie_kg = sum(p['kg'] for p in productores.values())
            
            # Omitir especies sin kg
            if especie_kg <= 0:
                continue
                
            especie_costo = sum(p['costo'] for p in productores.values())
            especie_costo_prom = (especie_costo / especie_kg) if especie_kg > 0 else None
            
            manejo_kg += especie_kg
            manejo_costo += especie_costo
            
            productores_list = []
            for prod_nombre, v in productores.items():
                kg = v['kg']
                # Omitir productores sin kg
                if kg <= 0:
                    continue
                costo = v['costo']
                costo_prom = (costo / kg) if kg > 0 else None
                productores_list.append({
                    'productor': prod_nombre,
                    'kg': kg,
                    'costo': costo,
                    'costo_prom': costo_prom
                })
            
            # Omitir especies sin productores válidos
            if not productores_list:
                continue
            
            # Ordenar productores por kg descendente
            productores_list.sort(key=lambda x: x['kg'], reverse=True)
            
            especies_list.append({
                'especie': especie,
                'kg': especie_kg,
                'costo': especie_costo,
                'costo_prom': especie_costo_prom,
                'productores': productores_list
            })
        
        # Omitir manejos sin especies válidas
        if not especies_list:
            continue
        
        # Ordenar especies por kg descendente
        especies_list.sort(key=lambda x: x['kg'], reverse=True)
        
        manejo_costo_prom = (manejo_costo / manejo_kg) if manejo_kg > 0 else None
        
        out.append({
            'manejo': manejo,
            'kg': manejo_kg,
            'costo': manejo_costo,
            'costo_prom': manejo_costo_prom,
            'especies': especies_list
        })
    
    return out
