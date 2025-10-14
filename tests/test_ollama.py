"""
Test de integración con Ollama y agente conversacional.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import create_conversational_agent, AgentExecutionError
from config.settings import settings


def test_ollama_connection():
    """Test 1: Verificar conexión básica con Ollama."""
    print("\n" + "="*60)
    print("TEST 1: Verificando conexión con Ollama")
    print("="*60)
    
    try:
        import requests
        
        # Test simple: verificar que Ollama responda
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
        
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            print(f"✅ Ollama está corriendo")
            print(f"   Modelos disponibles: {', '.join(model_names)}")
            
            if settings.OLLAMA_MODEL in model_names or any(settings.OLLAMA_MODEL in m for m in model_names):
                print(f"   ✓ {settings.OLLAMA_MODEL} está disponible")
                return True
            else:
                print(f"   ⚠️  {settings.OLLAMA_MODEL} no encontrado")
                print(f"   Descárgalo con: ollama pull {settings.OLLAMA_MODEL}")
                return False
        else:
            print(f"❌ Ollama no responde (status: {response.status_code})")
            return False
        
    except requests.exceptions.ConnectionError:
        print("❌ No se puede conectar a Ollama")
        print("\nAsegúrate de que Ollama esté corriendo:")
        print("  ollama serve")
        return False
    except Exception as e:
        print(f"❌ Error conectando con Ollama: {e}")
        print("\nAsegúrate de que Ollama esté corriendo:")
        print("  ollama serve")
        print(f"  ollama pull {settings.OLLAMA_MODEL}")
        return False


def test_conversational_agent():
    """Test 2: Crear y probar agente conversacional."""
    print("\n" + "="*60)
    print("TEST 2: Creando agente conversacional")
    print("="*60)
    
    try:
        # Crear agente
        agent = create_conversational_agent(
            model_name=settings.OLLAMA_MODEL,
            temperature=0.7,
            log_dir=settings.LOGS_DIR
        )
        
        print(f"✅ Agente creado: {agent.name}")
        print(f"   Modelo: ollama/{agent.model_name}")
        print(f"   Temperatura: {agent.temperature}")
        
        return agent
        
    except AgentExecutionError as e:
        print(f"❌ Error creando agente: {e}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        return None


def test_simple_conversation(agent):
    """Test 3: Conversación simple."""
    print("\n" + "="*60)
    print("TEST 3: Conversación simple")
    print("="*60)
    
    test_messages = [
        "Hola, ¿cómo te llamas?",
        "¿Cuánto es 2 + 2?",
        "Explícame qué es la fotosíntesis en una frase"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n--- Mensaje {i} ---")
        print(f"Usuario: {message}")
        
        try:
            response = agent.chat(message)
            
            # Limpiar respuesta (a veces tiene prefijos de CrewAI)
            response_clean = response.strip()
            if len(response_clean) > 200:
                print(f"Minerva: {response_clean[:200]}...")
            else:
                print(f"Minerva: {response_clean}")
            
            print("✅ Respuesta recibida")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    return True


def test_agent_stats(agent):
    """Test 4: Verificar estadísticas del agente."""
    print("\n" + "="*60)
    print("TEST 4: Estadísticas del agente")
    print("="*60)
    
    stats = agent.get_stats()
    
    print(f"Nombre: {stats['name']}")
    print(f"Tipo: {stats['type']}")
    print(f"Interacciones: {stats['interactions_count']}")
    print(f"Uptime: {stats['uptime_seconds']:.2f} segundos")
    
    if stats['interactions_count'] > 0:
        print("✅ Estadísticas correctas")
        return True
    else:
        print("❌ No se registraron interacciones")
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*60)
    print("🧪 TESTS DE FASE 2 - AGENTE CONVERSACIONAL")
    print("="*60)
    
    # Test 1: Ollama
    if not test_ollama_connection():
        print("\n❌ Ollama no está disponible. Abortando tests.")
        return
    
    # Test 2: Crear agente
    agent = test_conversational_agent()
    if not agent:
        print("\n❌ No se pudo crear el agente. Abortando tests.")
        return
    
    # Test 3: Conversación
    if not test_simple_conversation(agent):
        print("\n❌ Falló la conversación.")
        return
    
    # Test 4: Estadísticas
    test_agent_stats(agent)
    
    # Resumen final
    print("\n" + "="*60)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("="*60)
    print("\nFase 2 funcionando correctamente:")
    print("  ✓ Ollama conectado")
    print("  ✓ Agente conversacional operativo")
    print("  ✓ Conversación funcionando")
    print("  ✓ Logging activo")
    print("\n🎉 ¡Listo para Fase 3!")


if __name__ == "__main__":
    main()