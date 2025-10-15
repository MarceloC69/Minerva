"""
Test del sistema de procesamiento de documentos y RAG.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.processing import DocumentProcessor, DocumentIndexer
from src.embeddings import EmbeddingService
from src.memory import VectorMemory
from src.database import DatabaseManager
from config.settings import settings


def create_test_document():
    """Crea un documento de prueba."""
    test_dir = settings.DATA_DIR / "test_docs"
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "test_minerva.txt"
    
    content = """
    Minerva es un asistente de IA personal que corre completamente en local.
    
    Características principales:
    - Privacidad total: Todo se ejecuta en tu computadora
    - Memoria persistente: Recuerda conversaciones anteriores
    - Aprendizaje de documentos: Puede leer y aprender de tus archivos
    - Sistema de confianza: Diferencia entre conocimiento de alta, media y baja confianza
    
    Arquitectura:
    Minerva utiliza Ollama con el modelo Phi-3 para generación de texto.
    Para embeddings usa FastEmbed con el modelo all-MiniLM-L6-v2.
    La memoria vectorial se gestiona con Qdrant en modo local.
    Las conversaciones se guardan en SQLite.
    
    Futuro:
    En el futuro, Minerva tendrá capacidades de voz, cámara y control del sistema operativo.
    """
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return test_file


def test_document_processing():
    """Test 1: Procesar documento en chunks."""
    print("\n" + "="*60)
    print("TEST 1: Procesamiento de documentos")
    print("="*60)
    
    try:
        # Crear documento de prueba
        test_file = create_test_document()
        print(f"✅ Documento de prueba creado: {test_file}")
        
        # Procesar
        processor = DocumentProcessor(chunk_size=200, chunk_overlap=20)
        chunks = processor.process_file(test_file)
        
        print(f"✅ Documento procesado: {len(chunks)} chunks")
        
        # Mostrar algunos chunks
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n   Chunk {i}:")
            print(f"   {chunk.text[:100]}...")
        
        # Estadísticas
        stats = processor.get_stats(chunks)
        print(f"\n✅ Estadísticas:")
        print(f"   Total chunks: {stats['num_chunks']}")
        print(f"   Tamaño promedio: {stats['avg_chunk_size']} chars")
        print(f"   Total caracteres: {stats['total_chars']}")
        
        return chunks
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_document_indexing():
    """Test 2: Indexar documento completo."""
    print("\n" + "="*60)
    print("TEST 2: Indexado de documentos")
    print("="*60)
    
    try:
        # Crear documento
        test_file = create_test_document()
        
        # Configurar servicios
        test_qdrant_path = settings.DATA_DIR / "test_qdrant"
        test_db_path = settings.DATA_DIR / "test_docs_minerva.db"
        
        # Limpiar si existen
        if test_db_path.exists():
            test_db_path.unlink()
        
        # Crear servicios
        embedding_service = EmbeddingService(
           model_name=settings.EMBEDDING_MODEL
        )
        vector_memory = VectorMemory(
            path=str(test_qdrant_path),
            collection_name="test_knowledge",
            vector_size=settings.EMBEDDING_DIM
        )
        db_manager = DatabaseManager(test_db_path)
        
        # Crear indexador
        indexer = DocumentIndexer(
            vector_memory=vector_memory,
            db_manager=db_manager,
            embedding_service=embedding_service,
            chunk_size=200,
            chunk_overlap=20
        )
        
        print("✅ Servicios inicializados")
        
        # Indexar documento
        result = indexer.index_document(
            file_path=test_file,
            collection_name="test_knowledge"
        )
        
        if result['success']:
            print(f"✅ Documento indexado correctamente")
            print(f"   Chunks creados: {result['chunks_created']}")
            print(f"   Tiempo: {result['processing_time_seconds']:.2f}s")
            print(f"   ID en DB: {result['document_id']}")
        else:
            print(f"❌ Error: {result.get('error')}")
            return None
        
        return indexer
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_document_search(indexer):
    """Test 3: Buscar en documentos indexados."""
    print("\n" + "="*60)
    print("TEST 3: Búsqueda en documentos")
    print("="*60)
    
    test_queries = [
        "¿Qué es Minerva?",
        "¿Qué modelo usa Minerva?",
        "características de privacidad"
    ]
    
    try:
        for query in test_queries:
            print(f"\n📝 Consulta: '{query}'")
            
            results = indexer.search_documents(
                query=query,
                collection_name="test_knowledge",
                limit=3,
                score_threshold=0.2
            )
            
            print(f"   Resultados: {len(results)}")
            
            for i, result in enumerate(results, 1):
                score = result['score']
                text = result['payload']['text']
                print(f"\n   {i}. Score: {score:.3f}")
                print(f"      {text[:100]}...")
        
        print(f"\n✅ Búsqueda funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_context_retrieval(indexer):
    """Test 4: Recuperar contexto para RAG."""
    print("\n" + "="*60)
    print("TEST 4: Recuperación de contexto")
    print("="*60)
    
    try:
        query = "¿Cómo funciona la arquitectura de Minerva?"
        
        context = indexer.get_document_context(
            query=query,
            collection_name="test_knowledge",
            max_chunks=2
        )
        
        print(f"✅ Contexto recuperado ({len(context)} chars):")
        print("\n" + "─"*60)
        print(context[:500] + "...")
        print("─"*60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*60)
    print("🧪 TESTS DE FASE 3 - PROCESAMIENTO DE DOCUMENTOS")
    print("="*60)
    
    # Test 1: Procesar
    chunks = test_document_processing()
    if not chunks:
        print("\n❌ Falló procesamiento. Abortando.")
        return
    
    # Test 2: Indexar
    indexer = test_document_indexing()
    if not indexer:
        print("\n❌ Falló indexado. Abortando.")
        return
    
    # Test 3: Buscar
    if not test_document_search(indexer):
        print("\n❌ Falló búsqueda. Abortando.")
        return
    
    # Test 4: Contexto
    if not test_context_retrieval(indexer):
        print("\n❌ Falló recuperación de contexto.")
        return
    
    # Resumen
    print("\n" + "="*60)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("="*60)
    print("\nSistema de documentos funcionando:")
    print("  ✓ Procesamiento de documentos")
    print("  ✓ División en chunks")
    print("  ✓ Generación de embeddings")
    print("  ✓ Indexado en Qdrant + SQLite")
    print("  ✓ Búsqueda semántica")
    print("  ✓ Recuperación de contexto para RAG")
    print("\n🎯 Listo para continuar con Agente de Conocimiento!")


if __name__ == "__main__":
    main()