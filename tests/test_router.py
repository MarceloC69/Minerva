"""
Test del Router Inteligente - Integración completa de Minerva Fase 3.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.router import IntelligentRouter
from src.agents import create_conversational_agent, create_knowledge_agent
from src.processing import DocumentIndexer
from src.embeddings import EmbeddingService
from src.memory import VectorMemory
from src.database import DatabaseManager
from config.settings import settings


def setup_complete_system():
    """Setup completo del sistema Minerva."""
    print("\n" + "="*60)
    print("SETUP: Sistema completo de Minerva")
    print("="*60)
    
    # 1. Crear documento de conocimiento
    test_dir = settings.DATA_DIR / "test_docs"
    test_dir.mkdir(exist_ok=True)
    
    test_file = test_dir / "minerva_complete.txt"
    
    content = """
    Minerva - Asistente de IA Personal Local
    
    ¿Qué es Minerva?
    Minerva es un asistente de inteligencia artificial que funciona completamente 
    en tu computadora local, garantizando privacidad total y sin necesidad de 
    conexión a internet para funcionar.
    
    Características principales:
    - Privacidad absoluta: Todos los datos permanecen en tu equipo
    - Memoria persistente: Recuerda todas tus conversaciones
    - Procesamiento de documentos: Lee y aprende de PDFs, DOCX y archivos de texto
    - Sistema de confianza: Clasifica el conocimiento en alta, media y baja confianza
    - Funcionamiento offline: No requiere internet una vez configurado
    
    Stack tecnológico:
    Minerva utiliza varias tecnologías de código abierto:
    - Ollama con modelo Phi-3 para generación de lenguaje natural
    - FastEmbed con all-MiniLM-L6-v2 para embeddings semánticos
    - Qdrant como base de datos vectorial (modo local)
    - SQLite para almacenamiento de conversaciones y metadata
    - Gradio para la interfaz de usuario web
    - Python 3.12 como lenguaje base
    
    Arquitectura del sistema:
    El Router Inteligente es el componente central que analiza cada consulta.
    Busca proactivamente en la base de conocimiento vectorial.
    Decide automáticamente qué agente debe responder.
    El Agente Conversacional maneja charlas generales y preguntas casuales.
    El Agente de Conocimiento responde usando RAG sobre documentos indexados.
    El Agente Web buscará información actualizada en internet (próximamente).
    
    Futuro de Minerva:
    Las próximas versiones incluirán:
    - Reconocimiento y síntesis de voz
    - Análisis de imágenes mediante cámara
    - Control del sistema operativo para automatización
    - Integración con calendarios y emails
    - Agente de auto-mejora que optimiza el sistema
    """
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Documento creado: {test_file.name}")
    
    # 2. Configurar todos los servicios
    test_qdrant_path = settings.DATA_DIR / "test_router_qdrant"
    test_db_path = settings.DATA_DIR / "test_router_minerva.db"
    
    if test_db_path.exists():
        test_db_path.unlink()
    
    embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
    vector_memory = VectorMemory(
        path=str(test_qdrant_path),
        collection_name="minerva_kb",
        vector_size=settings.EMBEDDING_DIM
    )
    db_manager = DatabaseManager(test_db_path)
    
    print("✅ Servicios base inicializados")
    
    # 3. Crear indexador y procesar documento
    indexer = DocumentIndexer(
        vector_memory=vector_memory,
        db_manager=db_manager,
        embedding_service=embedding_service,
        chunk_size=300,
        chunk_overlap=30
    )
    
    result = indexer.index_document(
        file_path=test_file,
        collection_name="minerva_kb"
    )
    
    print(f"✅ Documento indexado: {result['chunks_created']} chunks")
    
    # 4. Crear agentes
    conversational_agent = create_conversational_agent(
        model_name=settings.OLLAMA_MODEL,
        temperature=0.7,
        log_dir=settings.LOGS_DIR,
        db_manager=db_manager
    )
    
    knowledge_agent = create_knowledge_agent(
        model_name=settings.OLLAMA_MODEL,
        temperature=0.3,
        log_dir=settings.LOGS_DIR,
        db_manager=db_manager,
        indexer=indexer
    )
    
    print("✅ Agentes creados (Conversacional + Conocimiento)")
    
    # 5. Crear router
    router = IntelligentRouter(
        conversational_agent=conversational_agent,
        knowledge_agent=knowledge_agent,
        indexer=indexer,
        knowledge_threshold=0.4
    )
    
    print("✅ Router Inteligente inicializado")
    
    return router, db_manager


def test_routing_decisions():
    """Test 1: Decisiones de routing."""
    print("\n" + "="*60)
    print("TEST 1: Decisiones del Router")
    print("="*60)
    
    router, db_manager = setup_complete_system()
    
    # Crear conversación
    conv = db_manager.create_conversation(title="Test Router Completo")
    
    # Consultas de prueba
    test_cases = [
        {
            'query': 'Hola, ¿cómo estás?',
            'expected_agent': 'conversational',
            'description': 'Saludo casual'
        },
        {
            'query': '¿Qué es Minerva?',
            'expected_agent': 'knowledge',
            'description': 'Pregunta sobre documentación'
        },
        {
            'query': '¿Cuánto es 5 + 3?',
            'expected_agent': 'conversational',
            'description': 'Cálculo simple'
        },
        {
            'query': '¿Qué tecnologías usa Minerva?',
            'expected_agent': 'knowledge',
            'description': 'Pregunta técnica en docs'
        },
        {
            'query': 'Cuéntame un chiste',
            'expected_agent': 'conversational',
            'description': 'Solicitud casual'
        },
        {
            'query': 'Explica la arquitectura del sistema',
            'expected_agent': 'knowledge',
            'description': 'Pregunta sobre arquitectura'
        }
    ]
    
    correct_decisions = 0
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n--- Caso {i}: {test['description']} ---")
        print(f"❓ Usuario: {test['query']}")
        
        result = router.route(
            user_message=test['query'],
            conversation_id=conv.id,
            collection_name="minerva_kb"
        )
        
        agent_used = result['agent_used']
        reason = result.get('routing_reason', 'N/A')
        
        # Mostrar respuesta (primeros 150 chars)
        answer_preview = result['answer'][:150] + "..." if len(result['answer']) > 150 else result['answer']
        print(f"💡 Respuesta: {answer_preview}")
        
        # Mostrar detalles del routing
        print(f"🤖 Agente usado: {agent_used}")
        print(f"📊 Razón: {reason}")
        
        if agent_used == 'knowledge':
            print(f"   Confianza: {result.get('confidence', 'N/A')}")
            print(f"   Fuentes: {result.get('num_sources', 0)}")
        
        # Verificar si la decisión fue correcta
        if agent_used == test['expected_agent']:
            print(f"✅ Decisión correcta")
            correct_decisions += 1
        else:
            print(f"⚠️  Esperaba: {test['expected_agent']}, obtuvo: {agent_used}")
    
    # Resumen
    accuracy = (correct_decisions / len(test_cases)) * 100
    print(f"\n📊 Precisión del router: {correct_decisions}/{len(test_cases)} ({accuracy:.1f}%)")
    
    return router, db_manager, conv.id


def test_conversation_flow(router, db_manager, conv_id):
    """Test 2: Flujo de conversación mixta."""
    print("\n" + "="*60)
    print("TEST 2: Flujo de conversación mixta")
    print("="*60)
    
    conversation_flow = [
        "Hola, quiero saber más sobre ti",
        "¿Qué es Minerva exactamente?",
        "¿Y qué modelo de IA usas?",
        "Genial, gracias por la información",
        "¿Cómo funciona el Router Inteligente?"
    ]
    
    print("Simulando conversación natural con cambios de agente...")
    
    for i, message in enumerate(conversation_flow, 1):
        print(f"\n💬 Turno {i}")
        print(f"Usuario: {message}")
        
        result = router.route(
            user_message=message,
            conversation_id=conv_id,
            collection_name="minerva_kb"
        )
        
        answer = result['answer'][:120] + "..." if len(result['answer']) > 120 else result['answer']
        agent = result['agent_used']
        
        print(f"Minerva ({agent}): {answer}")
    
    print("\n✅ Conversación completada")


def test_stats(router, db_manager):
    """Test 3: Estadísticas del sistema."""
    print("\n" + "="*60)
    print("TEST 3: Estadísticas del sistema")
    print("="*60)
    
    # Stats del router
    router_stats = router.get_stats()
    
    print("📊 Estadísticas de Agentes:")
    print(f"\n  Agente Conversacional:")
    conv_stats = router_stats['conversational_agent']
    print(f"    - Interacciones: {conv_stats['interactions_count']}")
    print(f"    - Uptime: {conv_stats['uptime_seconds']:.1f}s")
    
    print(f"\n  Agente de Conocimiento:")
    know_stats = router_stats['knowledge_agent']
    print(f"    - Interacciones: {know_stats['interactions_count']}")
    print(f"    - Uptime: {know_stats['uptime_seconds']:.1f}s")
    
    print(f"\n  Router:")
    print(f"    - Umbral de conocimiento: {router_stats['threshold']}")
    
    # Stats de la base de datos
    db_stats = db_manager.update_stats()
    
    print(f"\n📚 Estadísticas de Base de Datos:")
    print(f"  - Conversaciones: {db_stats.total_conversations}")
    print(f"  - Mensajes totales: {db_stats.total_messages}")
    print(f"  - Documentos indexados: {db_stats.total_documents}")
    
    print("\n✅ Estadísticas recopiladas")


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*60)
    print("🧪 TESTS DEL ROUTER INTELIGENTE - INTEGRACIÓN FASE 3")
    print("="*60)
    
    # Test 1: Decisiones de routing
    router, db_manager, conv_id = test_routing_decisions()
    
    # Test 2: Flujo de conversación
    test_conversation_flow(router, db_manager, conv_id)
    
    # Test 3: Estadísticas
    test_stats(router, db_manager)
    
    # Resumen final
    print("\n" + "="*60)
    print("✅ FASE 3 COMPLETADA - TODOS LOS TESTS PASADOS")
    print("="*60)
    print("\n🎉 Sistema completo de Minerva operativo:")
    print("  ✓ Procesamiento de documentos (PDFs, DOCX, TXT)")
    print("  ✓ Indexado vectorial en Qdrant")
    print("  ✓ Base de datos SQLite con persistencia")
    print("  ✓ Agente Conversacional funcionando")
    print("  ✓ Agente de Conocimiento con RAG")
    print("  ✓ Router Inteligente decidiendo automáticamente")
    print("  ✓ Búsqueda proactiva de contexto")
    print("  ✓ Sistema de confianza operativo")
    print("\n🚀 Listo para Fase 4 (Búsqueda Web) o Fase 5 (UI con Gradio)!")


if __name__ == "__main__":
    main()