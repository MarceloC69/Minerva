# tests/test_simple_memory.py
"""Script para probar SimpleMemoryService."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.embeddings import EmbeddingService
from src.memory import VectorMemory, get_simple_memory_service
from src.database import DatabaseManager
from config.settings import settings


def test_simple_memory():
    """Prueba la memoria simple."""
    
    print("🧠 Probando SimpleMemoryService")
    print("=" * 60)
    
    # 1. Inicializar componentes
    print("\n1. Inicializando componentes...")
    embedding_service = EmbeddingService()
    vector_memory = VectorMemory(
        path=str(settings.QDRANT_STORAGE_PATH),
        collection_name="test_collection",
        vector_size=settings.EMBEDDING_DIM
    )
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    
    memory = get_simple_memory_service(
        embedding_service=embedding_service,
        vector_memory=vector_memory,
        db_manager=db_manager
    )
    print("✅ Componentes inicializados")
    
    # 2. Memorizar información
    print("\n2. Memorizando información...")
    facts_to_remember = [
        "Me llamo Marcelo",
        "Soy desarrollador Python",
        "Me gusta la ciencia ficción",
        "Vivo en Guernica, Buenos Aires"
    ]
    
    for fact in facts_to_remember:
        result = memory.remember(fact)
        if result['success']:
            print(f"   ✅ {fact} → {result['facts_count']} hechos")
        else:
            print(f"   ❌ Error: {result.get('error')}")
    
    # 3. Recordar información
    print("\n3. Recordando información...")
    queries = [
        "¿Cómo me llamo?",
        "¿Cuál es mi profesión?",
        "¿Qué me gusta?",
        "¿Dónde vivo?"
    ]
    
    for query in queries:
        print(f"\n   Query: {query}")
        facts = memory.recall(query, limit=2)
        if facts:
            for i, fact in enumerate(facts, 1):
                print(f"      {i}. {fact}")
        else:
            print("      (No se encontró información)")
    
    # 4. Contexto para LLM
    print("\n4. Generando contexto para LLM...")
    context = memory.get_context("háblame de mí")
    if context:
        print(context)
    else:
        print("   (No hay contexto)")
    
    print("\n" + "=" * 60)
    print("✅ Prueba completada")


if __name__ == "__main__":
    try:
        test_simple_memory()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
