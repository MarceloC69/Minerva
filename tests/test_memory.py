# tests/test_memory.py
"""
Script para probar la memoria persistente de Minerva.
"""

import sys
from pathlib import Path

# Agregar raíz del proyecto al path (estamos en tests/)
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.memory_service import get_memory_service
from src.database import DatabaseManager
from config.settings import settings


def test_memory():
    """Prueba básica de memoria persistente."""
    
    print("🧠 Probando Memoria Persistente de Minerva")
    print("=" * 60)
    
    # Inicializar componentes
    print("\n1. Inicializando componentes...")
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    memory_service = get_memory_service(db_manager=db_manager)
    print("✅ Componentes inicializados")
    
    # Test 1: Agregar información
    print("\n2. Agregando información a la memoria...")
    test_facts = [
        "El usuario se llama Marcelo",
        "Marcelo es desarrollador Python",
        "A Marcelo le gusta la ciencia ficción",
        "Marcelo vive en Guernica, Buenos Aires, Argentina"
    ]
    
    for fact in test_facts:
        result = memory_service.add_memory(
            text=fact,
            user_id="default_user",
            metadata={'test': True}
        )
        if result['success']:
            print(f"   ✅ Memorizado: {fact}")
        else:
            print(f"   ❌ Error: {result.get('error')}")
    
    # Test 2: Buscar información
    print("\n3. Buscando información relevante...")
    queries = [
        "¿Cómo se llama el usuario?",
        "¿Qué le gusta al usuario?",
        "¿Dónde vive?",
        "¿Cuál es su profesión?"
    ]
    
    for query in queries:
        print(f"\n   Query: {query}")
        results = memory_service.search_memory(
            query=query,
            user_id="default_user",
            limit=2
        )
        
        if results:
            for i, mem in enumerate(results, 1):
                if isinstance(mem, dict):
                    memory_text = mem.get('memory', mem.get('text', str(mem)))
                else:
                    memory_text = str(mem)
                print(f"      {i}. {memory_text}")
        else:
            print("      (No se encontró información)")
    
    # Test 3: Obtener todas las memorias
    print("\n4. Obteniendo todas las memorias...")
    all_memories = memory_service.get_all_memories(user_id="default_user")
    print(f"   Total de memorias: {len(all_memories)}")
    
    if all_memories:
        print("\n   Memorias almacenadas:")
        for i, mem in enumerate(all_memories, 1):
            if isinstance(mem, dict):
                memory_text = mem.get('memory', mem.get('text', str(mem)))
            else:
                memory_text = str(mem)
            print(f"      {i}. {memory_text}")
    
    # Test 4: Contexto para LLM
    print("\n5. Generando contexto para LLM...")
    context = memory_service.get_memory_context(
        query="Háblame del usuario",
        user_id="default_user",
        limit=3
    )
    
    if context:
        print("   Contexto generado:")
        print(context)
    else:
        print("   (No hay contexto)")
    
    print("\n" + "=" * 60)
    print("✅ Prueba de memoria completada")
    print("\n💡 Tip: Ahora puedes iniciar Minerva y preguntarle:")
    print("   - '¿Qué recuerdas de mí?'")
    print("   - '¿Cómo me llamo?'")
    print("   - '¿Qué sabes sobre mí?'")


if __name__ == "__main__":
    try:
        test_memory()
    except Exception as e:
        print(f"\n❌ Error durante la prueba: {e}")
        import traceback
        traceback.print_exc()