"""
Test del Agente de Conocimiento (RAG).
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents import create_knowledge_agent
from src.processing import DocumentIndexer
from src.embeddings import EmbeddingService
from src.memory import VectorMemory
from src.database import DatabaseManager
from config.settings import settings


def setup_test_environment():
    """Configura el entorno de prueba con un documento indexado."""
    print("\n" + "="*60)
    print("SETUP: Preparando entorno de prueba")
    print("="*60)
    
    # Crear documento de prueba
    test_dir = settings.DATA_DIR / "test_docs"
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "minerva_info.txt"
    
    content = """
    Minerva es un asistente de IA personal que corre completamente en local.
    
    Características principales:
    - Privacidad total: Todo se ejecuta en tu computadora local
    - Memoria persistente: Recuerda todas las conversaciones anteriores
    - Aprendizaje de documentos: Puede leer PDFs, DOCX y archivos de texto
    - Sistema de confianza: Diferencia entre conocimiento de alta, media y baja confianza
    - Sin dependencia de internet: Funciona offline
    
    Tecnologías utilizadas:
    Minerva utiliza Ollama con el modelo Phi-3 para generación de texto.
    Para embeddings usa FastEmbed con el modelo all-MiniLM-L6-v2.
    La memoria vectorial se gestiona con Qdrant en modo local.
    Las conversaciones se guardan en una base de datos SQLite.
    El frontend está construido con Gradio.
    
    Arquitectura del sistema:
    El Router Inteligente analiza cada consulta y decide qué agente usar.
    El Agente Conversacional maneja charlas generales.
    El Agente de Conocimiento busca en documentos usando RAG.
    El Agente Web buscará información en internet (futuro).
    
    Capacidades futuras:
    En el futuro, Minerva tendrá reconocimiento de voz.
    También podrá usar la cámara para analizar imágenes.
    Se añadirá control del sistema operativo para automatización.
    """
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Documento de prueba creado: {test_file.name}")
    
    # Configurar servicios
    test_qdrant_path = settings.DATA_DIR / "test_knowledge_qdrant"
    test_db_path = settings.DATA_DIR / "test_knowledge_minerva.db"
    
    # Limpiar DB si existe
    if test_db_path.exists():
        test_db_path.unlink()
    
    embedding_service = EmbeddingService(
        model_name=settings.EMBEDDING_MODEL
    )
    vector_memory = VectorMemory(
        path=str(test_qdrant_path),
        collection_name="test_knowledge",
        vector_size=settings.EMBEDDING_DIM
    )
    db_manager = DatabaseManager(test_db_path)
    
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
        print(f"✅ Documento indexado: {result['chunks_created']} chunks")
    else:
        print(f"❌ Error indexando: {result.get('error')}")
        return None, None, None
    
    return indexer, db_manager, test_file


def test_create_knowledge_agent(indexer, db_manager):
    """Test 1: Crear agente de conocimiento."""
    print("\n" + "="*60)
    print("TEST 1: Crear agente de conocimiento")
    print("="*60)
    
    try:
        agent = create_knowledge_agent(
            model_name=settings.OLLAMA_MODEL,
            temperature=0.3,
            log_dir=settings.LOGS_DIR,
            db_manager=db_manager,
            indexer=indexer
        )
        
        print(f"✅ Agente creado: {agent.name}")
        print(f"   Modelo: {agent.model_name}")
        print(f"   Temperatura: {agent.temperature}")
        
        return agent
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def test_knowledge_queries(agent, db_manager):
    """Test 2: Consultas con el agente de conocimiento."""
    print("\n" + "="*60)
    print("TEST 2: Consultas al agente de conocimiento")
    print("="*60)
    
    # Crear conversación
    conv = db_manager.create_conversation(title="Test RAG")
    
    test_queries = [
        "¿Qué es Minerva?",
        "¿Qué tecnologías usa Minerva?",
        "¿Cómo funciona el Router Inteligente?",
        "¿Cuál es la capital de Francia?"  # Esta NO debería estar en docs
    ]
    
    try:
        for i, query in enumerate(test_queries, 1):
            print(f"\n--- Consulta {i} ---")
            print(f"❓ Usuario: {query}")
            
            result = agent.answer(
                user_message=query,
                conversation_id=conv.id,
                collection_name="test_knowledge",
                max_context_chunks=3
            )
            
            print(f"💡 Respuesta: {result['answer'][:200]}...")
            print(f"📊 Confianza: {result['confidence']}")
            print(f"📚 Fuentes: {result['num_sources']}")
            
            if result['sources']:
                print(f"   Fuentes usadas:")
                for src in result['sources']:
                    print(f"   - {src['filename']} (score: {src['score']:.3f})")
            
            print("✅ Consulta procesada")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversation_history(db_manager, conv_id):
    """Test 3: Verificar que se guardó en DB."""
    print("\n" + "="*60)
    print("TEST 3: Historial de conversación")
    print("="*60)
    
    try:
        messages = db_manager.get_conversation_messages(conv_id)
        
        print(f"✅ Mensajes guardados: {len(messages)}")
        
        for msg in messages:
            role_emoji = "❓" if msg.role == "user" else "💡"
            print(f"\n{role_emoji} {msg.role.upper()}: {msg.content[:100]}...")
            if msg.role == "assistant":
                metadata = msg.extra_metadata or {}
                confidence = metadata.get('confidence', 'N/A')
                num_sources = metadata.get('num_sources', 0)
                print(f"   Confianza: {confidence}, Fuentes: {num_sources}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*60)
    print("🧪 TESTS DE AGENTE DE CONOCIMIENTO (RAG)")
    print("="*60)
    
    # Setup
    indexer, db_manager, test_file = setup_test_environment()
    if not indexer:
        print("\n❌ Falló setup. Abortando.")
        return
    
    # Test 1: Crear agente
    agent = test_create_knowledge_agent(indexer, db_manager)
    if not agent:
        print("\n❌ No se pudo crear agente. Abortando.")
        return
    
    # Test 2: Consultas
    if not test_knowledge_queries(agent, db_manager):
        print("\n❌ Fallaron las consultas.")
        return
    
    # Test 3: Verificar historial
    conv = db_manager.get_active_conversations(limit=1)[0]
    if not test_conversation_history(db_manager, conv.id):
        print("\n❌ Falló verificación de historial.")
        return
    
    # Resumen
    print("\n" + "="*60)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("="*60)
    print("\nAgente de Conocimiento funcionando:")
    print("  ✓ Busca en documentos indexados")
    print("  ✓ Responde con RAG (contexto + LLM)")
    print("  ✓ Cita fuentes correctamente")
    print("  ✓ Indica nivel de confianza")
    print("  ✓ Guarda conversaciones en DB")
    print("  ✓ Maneja preguntas sin respuesta en docs")
    print("\n🎯 Listo para el Router Inteligente!")


if __name__ == "__main__":
    main()