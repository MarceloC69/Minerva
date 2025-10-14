import sys
from pathlib import Path

# Agregar el directorio raíz al PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from src.embeddings.embedder import EmbeddingService
from src.memory.vector_store import VectorMemory
from config.settings import Settings

def test_memory_system():
    """Test del sistema de memoria con embeddings y vector store"""
    print("=" * 60)
    print("🧪 TEST: Sistema de Memoria")
    print("=" * 60)
    
    # Setup
    print("\n1. Inicializando configuración...")
    settings = Settings()
    
    print("\n2. Inicializando servicio de embeddings...")
    embedder = EmbeddingService(settings.EMBEDDING_MODEL)
    
    print("\n3. Inicializando almacenamiento vectorial...")
    memory = VectorMemory(
        path=settings.QDRANT_PATH,
        collection_name="test_collection",
        vector_size=settings.EMBEDDING_DIMENSIONS
    )
    
    # Test 1: Guardar
    print("\n" + "=" * 60)
    print("TEST 1: Guardando textos con embeddings")
    print("=" * 60)
    
    texts = [
        "Python es un lenguaje de programación",
        "Me gusta programar en Python",
        "El clima está soleado hoy"
    ]
    
    print(f"\nTextos a guardar:")
    for i, text in enumerate(texts, 1):
        print(f"  {i}. {text}")
    
    print("\nGenerando embeddings...")
    embeddings = embedder.embed_texts(texts)
    print(f"✓ Generados {len(embeddings)} embeddings de dimensión {len(embeddings[0])}")
    
    metadata = [
        {"source": "doc1", "confidence": "high"},
        {"source": "doc2", "confidence": "high"},
        {"source": "doc3", "confidence": "low"}
    ]
    
    print("\nGuardando en Qdrant...")
    ids = memory.add_texts(texts, embeddings, metadata)
    print(f"✓ Guardados {len(ids)} textos con IDs:")
    for id_ in ids:
        print(f"  - {id_}")
    
    # Test 2: Buscar
    print("\n" + "=" * 60)
    print("TEST 2: Búsqueda semántica")
    print("=" * 60)
    
    query = "lenguajes de programación"
    print(f"\nConsulta: '{query}'")
    
    print("Generando embedding de consulta...")
    query_emb = embedder.embed_single(query)
    
    print("Buscando en Qdrant...")
    results = memory.search(query_emb, top_k=2)
    
    print(f"\n✓ Encontrados {len(results)} resultados:")
    for i, result in enumerate(results, 1):
        print(f"\n  Resultado {i}:")
        print(f"    Score: {result['score']:.4f}")
        print(f"    Texto: {result['text']}")
        print(f"    Metadata: {result['metadata']}")
    
    # Limpieza
    print("\n" + "=" * 60)
    print("LIMPIEZA: Eliminando colección de test")
    print("=" * 60)
    memory.delete_collection()
    
    print("\n" + "=" * 60)
    print("✅ TODOS LOS TESTS PASARON CORRECTAMENTE")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_memory_system()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)