#!/usr/bin/env python3
"""
Script de prueba para verificar la integración con Ollama
"""
import asyncio
import httpx
import json

OLLAMA_URL = "http://localhost:11434"
MODEL = "granite4"

async def test_ollama_connection():
    """Prueba la conexión con Ollama"""
    print("🔍 Verificando conexión con Ollama...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                print(f"✅ Conectado a Ollama")
                print(f"📦 Modelos disponibles: {len(models)}")
                for model in models:
                    print(f"   - {model['name']}")
                return True
            else:
                print(f"❌ Error al conectar: {response.status_code}")
                return False
                
    except httpx.ConnectError:
        print("❌ No se pudo conectar con Ollama")
        print("💡 Asegúrate de que Ollama esté corriendo: ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return False

async def test_model_availability():
    """Verifica que el modelo esté disponible"""
    print(f"\n🔍 Verificando modelo {MODEL}...")
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{OLLAMA_URL}/api/tags")
            
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                
                if MODEL in model_names or f"{MODEL}:latest" in model_names:
                    print(f"✅ Modelo {MODEL} está disponible")
                    return True
                else:
                    print(f"❌ Modelo {MODEL} no está disponible")
                    print(f"💡 Descarga el modelo con: ollama pull {MODEL}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error al verificar modelo: {e}")
        return False

async def test_generation():
    """Prueba la generación de texto"""
    print(f"\n🔍 Probando generación de texto...")
    
    prompt = "Resume en 2 oraciones qué es la trazabilidad agroalimentaria."
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            print(f"📝 Prompt: {prompt}")
            print("⏳ Generando respuesta...")
            
            response = await client.post(
                f"{OLLAMA_URL}/api/generate",
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 100
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                text = result.get("response", "")
                print(f"\n✅ Respuesta generada:")
                print(f"   {text}")
                return True
            else:
                print(f"❌ Error en generación: {response.status_code}")
                return False
                
    except httpx.TimeoutException:
        print("❌ Timeout al generar respuesta")
        print("💡 El modelo puede tardar más en la primera ejecución")
        return False
    except Exception as e:
        print(f"❌ Error al generar: {e}")
        return False

async def main():
    """Ejecuta todas las pruebas"""
    print("=" * 60)
    print("🧪 Test de Integración con Ollama")
    print("=" * 60)
    
    # Test 1: Conexión
    if not await test_ollama_connection():
        print("\n❌ Pruebas fallidas: No se pudo conectar con Ollama")
        return
    
    # Test 2: Modelo disponible
    if not await test_model_availability():
        print("\n❌ Pruebas fallidas: Modelo no disponible")
        return
    
    # Test 3: Generación
    if not await test_generation():
        print("\n❌ Pruebas fallidas: Error en generación")
        return
    
    print("\n" + "=" * 60)
    print("✅ Todas las pruebas pasaron exitosamente")
    print("=" * 60)
    print("\n💡 La integración con IA está lista para usar!")

if __name__ == "__main__":
    asyncio.run(main())
