"""
Servicio para integración con Ollama (modelo de IA local)
"""
import httpx
import json
import logging
import traceback
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class AIService:
    """Servicio para generar resúmenes de trazabilidad usando Ollama"""
    
    def __init__(self, ollama_url: str = None):
        # Usar variable de entorno o default
        # En Docker Linux, usar host.docker.internal o la IP del gateway
        import os
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL", "http://172.17.0.1:11434")
        # Usar modelo pequeño para velocidad en CPU
        self.model = os.getenv("OLLAMA_MODEL", "llama3.2")
        
    async def generate_traceability_summary(
        self,
        search_context: Dict[str, Any],
        traceability_data: Dict[str, Any]
    ) -> str:
        """
        Genera un resumen de trazabilidad usando IA
        
        Args:
            search_context: Contexto de búsqueda (tipo, parámetros, fechas, etc.)
            traceability_data: Datos completos de trazabilidad
            
        Returns:
            Resumen generado por la IA
        """
        # Construir el prompt según el contexto
        try:
            print(f"[AIService] Generando resumen para search_type: {search_context.get('search_type')}", flush=True)
            prompt = self._build_prompt(search_context, traceability_data)
            print(f"[AIService] Prompt construido: {len(prompt)} caracteres", flush=True)
        except Exception as e:
            logger.error(f"[AIService] Error construyendo prompt: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error construyendo prompt: {type(e).__name__}: {str(e)}"
        
        try:
            print(f"[AIService] Conectando a Ollama: {self.ollama_url}", flush=True)
            print(f"[AIService] Modelo: {self.model}", flush=True)
            print(f"[AIService] Longitud del prompt: {len(prompt)} caracteres", flush=True)
            
            async with httpx.AsyncClient(timeout=120.0) as client:
                url = f"{self.ollama_url}/api/generate"
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "top_p": 0.9,
                        "num_predict": 250,
                    }
                }
                
                print(f"[AIService] POST a {url}", flush=True)
                print(f"[AIService] Payload model: {payload['model']}, prompt length: {len(payload['prompt'])}", flush=True)
                
                response = await client.post(url, json=payload)
                
                print(f"[AIService] Respuesta recibida: {response.status_code}", flush=True)
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("response", "No se pudo generar el resumen.")
                else:
                    return f"Error al conectar con Ollama: {response.status_code}"
                    
        except httpx.ConnectError as e:
            logger.error(f"[AIService] Error de conexión: {str(e)}")
            logger.error(f"[AIService] URL: {self.ollama_url}")
            logger.error(traceback.format_exc())
            return "⚠️ No se pudo conectar con Ollama. Asegúrate de que el servicio esté corriendo (ollama serve) y escuchando en 0.0.0.0:11434."
        except httpx.TimeoutException as e:
            logger.error(f"[AIService] Timeout: {str(e)}")
            logger.error(f"[AIService] URL: {self.ollama_url}")
            logger.error(f"[AIService] El timeout fue de 120 segundos")
            return "⏱️ Timeout esperando respuesta de Ollama."
        except Exception as e:
            logger.error(f"[AIService] Error inesperado: {type(e).__name__}: {str(e)}")
            logger.error(traceback.format_exc())
            return f"Error inesperado: {type(e).__name__}: {str(e)}"
    
    def _build_prompt(self, context: Dict[str, Any], data: Dict[str, Any]) -> str:
        """Construye el prompt según el tipo de búsqueda"""
        
        search_type = context.get("search_type", "unknown")
        
        # Extraer estadísticas clave
        stats = self._extract_stats(data)
        
        # Prompt base
        base_prompt = """Eres un asistente experto en trazabilidad agroalimentaria. Tu trabajo es analizar datos de trazabilidad y generar resúmenes claros, concisos y accionables en español.

IMPORTANTE: 
- Sé específico con números y nombres
- Menciona fechas importantes
- Identifica el flujo completo (origen → destino)
- Resalta cualquier anomalía o patrón relevante
- Usa lenguaje profesional pero claro
- Máximo 300 palabras

"""
        
        # Agregar contexto específico según el tipo de búsqueda
        if search_type == "sale":
            context_prompt = self._build_sale_context(context, stats)
        elif search_type == "date_range":
            context_prompt = self._build_date_range_context(context, stats)
        elif search_type == "pallet":
            context_prompt = self._build_pallet_context(context, stats)
        elif search_type == "guide":
            context_prompt = self._build_guide_context(context, stats)
        else:
            context_prompt = self._build_generic_context(context, stats)
        
        return base_prompt + context_prompt
    
    def _extract_stats(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Extrae estadísticas relevantes de los datos de trazabilidad"""
        
        pallets = data.get("pallets", {})
        processes = data.get("processes", {})
        suppliers = data.get("suppliers", {})
        customers = data.get("customers", {})
        links = data.get("links", [])
        
        # Contar recepciones y procesos
        receptions = {ref: p for ref, p in processes.items() if p.get("is_reception")}
        production_processes = {ref: p for ref, p in processes.items() if not p.get("is_reception")}
        
        # Calcular pesos totales
        total_weight_in = sum(p.get("qty_done", 0) for p in pallets.values() if p.get("move_type") in ["in", "internal"])
        total_weight_out = sum(p.get("qty_done", 0) for p in pallets.values() if p.get("move_type") == "out")
        
        # Extraer nombres de proveedores y clientes
        supplier_names = [s.get("name", "Desconocido") for s in suppliers.values()]
        customer_names = [c.get("name", "Desconocido") for c in customers.values()]
        
        # Extraer fechas
        dates = []
        for p in pallets.values():
            if p.get("pack_date"):
                dates.append(p["pack_date"])
            elif p.get("date"):
                dates.append(p["date"])
        
        return {
            "total_pallets": len(pallets),
            "total_receptions": len(receptions),
            "total_processes": len(production_processes),
            "total_suppliers": len(suppliers),
            "total_customers": len(customers),
            "total_links": len(links),
            "total_weight_in": total_weight_in,
            "total_weight_out": total_weight_out,
            "supplier_names": supplier_names[:5],  # Top 5
            "customer_names": customer_names[:5],  # Top 5
            "date_range": {
                "min": min(dates) if dates else None,
                "max": max(dates) if dates else None
            }
        }
    
    def _build_sale_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por venta"""
        sale_id = context.get("sale_id", "N/A")
        customer = context.get("customer_name", "Cliente desconocido")
        
        # Safe formatting
        weight_out = stats['total_weight_out']
        weight_str = f"{weight_out:.2f} kg" if weight_out else "N/A"
        date_min = stats['date_range']['min'] or "N/A"
        date_max = stats['date_range']['max'] or "N/A"
        suppliers_str = ', '.join(stats['supplier_names']) if stats['supplier_names'] else 'N/A'
        
        return f"""
CONTEXTO: Trazabilidad de venta
- ID de Venta: {sale_id}
- Cliente: {customer}

DATOS:
- Total de pallets enviados: {stats['total_pallets']}
- Peso total: {weight_str}
- Procesos involucrados: {stats['total_processes']}
- Proveedores origen: {suppliers_str}
- Rango de fechas: {date_min} a {date_max}

TAREA: Genera un resumen ejecutivo de la trazabilidad de esta venta. Describe:
1. El origen de los productos (proveedores y fechas de recepción)
2. Los procesos de transformación aplicados
3. El destino final (cliente y fecha de despacho)
4. Cualquier observación relevante sobre tiempos o volúmenes
"""
    
    def _build_date_range_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por rango de fechas"""
        start_date = context.get("start_date", "N/A")
        end_date = context.get("end_date", "N/A")
        
        # Safe formatting
        weight_in = stats['total_weight_in']
        weight_out = stats['total_weight_out']
        weight_in_str = f"{weight_in:.2f} kg" if weight_in else "N/A"
        weight_out_str = f"{weight_out:.2f} kg" if weight_out else "N/A"
        suppliers_str = ', '.join(stats['supplier_names'][:3]) if stats['supplier_names'] else 'N/A'
        customers_str = ', '.join(stats['customer_names'][:3]) if stats['customer_names'] else 'N/A'
        
        return f"""
CONTEXTO: Trazabilidad por rango de fechas
- Período: {start_date} a {end_date}

DATOS:
- Total de pallets: {stats['total_pallets']}
- Recepciones: {stats['total_receptions']}
- Procesos de producción: {stats['total_processes']}
- Proveedores activos: {stats['total_suppliers']} ({suppliers_str})
- Clientes atendidos: {stats['total_customers']} ({customers_str})
- Peso total procesado: {weight_in_str}
- Peso total despachado: {weight_out_str}

TAREA: Genera un resumen del flujo de trazabilidad en este período. Describe:
1. Volumen de recepciones y principales proveedores
2. Actividad de producción y transformación
3. Despachos y principales clientes
4. Eficiencia del flujo (mermas, tiempos, etc.)
"""
    
    def _build_pallet_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por pallet específico"""
        pallet_id = context.get("pallet_id", "N/A")
        pallet_name = context.get("pallet_name", "N/A")
        
        # Safe formatting
        date_min = stats['date_range']['min'] or "N/A"
        date_max = stats['date_range']['max'] or "N/A"
        suppliers_str = ', '.join(stats['supplier_names']) if stats['supplier_names'] else 'Producción interna'
        customers_str = ', '.join(stats['customer_names']) if stats['customer_names'] else 'Stock interno'
        
        return f"""
CONTEXTO: Trazabilidad de pallet específico
- ID Pallet: {pallet_id}
- Nombre: {pallet_name}

DATOS:
- Proveedores origen: {suppliers_str}
- Procesos aplicados: {stats['total_processes']}
- Cliente destino: {customers_str}
- Rango temporal: {date_min} a {date_max}
- Enlaces en la cadena: {stats['total_links']}

TAREA: Genera un resumen detallado de la trazabilidad de este pallet. Describe:
1. Origen completo (proveedor, recepción, fecha)
2. Transformaciones y procesos aplicados
3. Destino final (cliente y fecha)
4. Tiempo total del flujo y observaciones relevantes
"""
    
    def _build_guide_context(self, context: Dict, stats: Dict) -> str:
        """Prompt para búsqueda por guía de despacho"""
        guide_number = context.get("guide_number", "N/A")
        
        # Safe formatting
        weight_out = stats['total_weight_out']
        weight_str = f"{weight_out:.2f} kg" if weight_out else "N/A"
        suppliers_str = ', '.join(stats['supplier_names']) if stats['supplier_names'] else 'N/A'
        customers_str = ', '.join(stats['customer_names']) if stats['customer_names'] else 'N/A'
        date_max = stats['date_range']['max'] or "N/A"
        
        return f"""
CONTEXTO: Trazabilidad por guía de despacho
- Guía de Despacho: {guide_number}

DATOS:
- Pallets en la guía: {stats['total_pallets']}
- Peso total: {weight_str}
- Proveedores origen: {suppliers_str}
- Procesos involucrados: {stats['total_processes']}
- Cliente destino: {customers_str}
- Fecha: {date_max}

TAREA: Genera un resumen de la trazabilidad de esta guía de despacho. Describe:
1. Composición del despacho (pallets y productos)
2. Origen de los materiales (proveedores y fechas)
3. Procesos aplicados antes del despacho
4. Observaciones sobre calidad o conformidad
"""
    
    def _build_generic_context(self, context: Dict, stats: Dict) -> str:
        """Prompt genérico"""
        
        # Safe formatting
        weight_in = stats['total_weight_in']
        weight_out = stats['total_weight_out']
        weight_in_str = f"{weight_in:.2f} kg" if weight_in else "N/A"
        weight_out_str = f"{weight_out:.2f} kg" if weight_out else "N/A"
        
        return f"""
CONTEXTO: Análisis de trazabilidad general

DATOS:
- Total de pallets: {stats['total_pallets']}
- Recepciones: {stats['total_receptions']}
- Procesos: {stats['total_processes']}
- Proveedores: {stats['total_suppliers']}
- Clientes: {stats['total_customers']}
- Peso entrada: {weight_in_str}
- Peso salida: {weight_out_str}

TAREA: Genera un resumen general del flujo de trazabilidad. Describe el flujo completo desde proveedores hasta clientes, destacando volúmenes, procesos clave y observaciones relevantes.
"""


# Instancia global del servicio
ai_service = AIService()
