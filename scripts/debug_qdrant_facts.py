#!/usr/bin/env python3
"""
Script para ver qué hechos están almacenados en Qdrant.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


from src.memory.vector_store import VectorMemory
from src.embeddings import EmbeddingService
from config.settings import settings

def main():
    print("=" * 60)
    print("🔍 DEBUG: Verificando hechos en Qdrant")
    print("=" * 60)
    
    # Inicializar componentes
    print("\n1. Inicializando componentes...")
    embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
    vector_memory = VectorMemory(
        path=str(settings.QDRANT_STORAGE_PATH),
        collection_name=settings.QDRANT_COLLECTION_NAME,
        vector_size=settings.EMBEDDING_DIM
    )
    
    print("✅ Componentes inicializados")
    
    # Ver info de la colección
    print("\n2. Info de la colección:")
    try:
        info = vector_memory.get_collection_info()
        print(f"   - Nombre: {info['name']}")
        print(f"   - Vectores: {info['vectors_count']}")
        print(f"   - Puntos: {info['points_count']}")
        print(f"   - Estado: {info['status']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Buscar hechos con diferentes queries
    print("\n3. Buscando hechos almacenados:")
    
    test_queries = [
        "Marcelo",
        "Buenos Aires",
        "nombre",
        "ciudad",
        "vive"
    ]
    
    for query in test_queries:
        print(f"\n   Query: '{query}'")
        try:
            # Generar embedding
            query_embedding = embedding_service.embed_text(query)
            
            # Buscar en Qdrant
            results = vector_memory.search(
                query_embedding=query_embedding,
                limit=5
            )
            
            if results:
                print(f"   ✅ Encontrados {len(results)} resultados:")
                for i, r in enumerate(results, 1):
                    payload = r.get('payload', {})
                    text = payload.get('text', 'Sin texto')
                    type_val = payload.get('type', 'Sin tipo')
                    score = r.get('score', 0)
                    
                    print(f"      {i}. [{type_val}] Score: {score:.3f}")
                    print(f"         {text}")
            else:
                print(f"   ⚪ No se encontraron resultados")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Listar TODOS los puntos (si no son muchos)
    print("\n4. Intentando listar todos los puntos...")
    try:
        # Buscar con query genérico para obtener todo
        query_embedding = embedding_service.embed_text("información")
        all_results = vector_memory.search(
            query_embedding=query_embedding,
            limit=50
        )
        
        if all_results:
            print(f"   Total de puntos recuperados: {len(all_results)}")
            
            # Filtrar solo hechos
            facts = [r for r in all_results if r.get('payload', {}).get('type') == 'fact']
            
            if facts:
                print(f"\n   ✅ HECHOS ALMACENADOS ({len(facts)}):")
                for i, fact in enumerate(facts, 1):
                    payload = fact.get('payload', {})
                    text = payload.get('text', 'Sin texto')
                    category = payload.get('category', 'Sin categoría')
                    
                    print(f"\n   {i}. Categoría: {category}")
                    print(f"      Texto: {text}")
            else:
                print("\n   ⚠️ NO HAY HECHOS ALMACENADOS (type='fact')")
                print("\n   Puntos encontrados por tipo:")
                types = {}
                for r in all_results:
                    t = r.get('payload', {}).get('type', 'sin_tipo')
                    types[t] = types.get(t, 0) + 1
                
                for type_name, count in types.items():
                    print(f"      - {type_name}: {count}")
        else:
            print("   ⚠️ La colección está VACÍA")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("✅ Debug completado")
    print("=" * 60)

if __name__ == "__main__":
    main()