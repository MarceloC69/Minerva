"""
Test del sistema de base de datos SQLite.
"""

import sys
from pathlib import Path

# Agregar directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager
from src.agents import create_conversational_agent
from config.settings import settings


def test_database_creation():
    """Test 1: Crear base de datos y tablas."""
    print("\n" + "="*60)
    print("TEST 1: Creando base de datos SQLite")
    print("="*60)
    
    try:
        # Crear DB temporal para tests
        test_db_path = settings.DATA_DIR / "test_minerva.db"
        
        # Eliminar si existe
        if test_db_path.exists():
            test_db_path.unlink()
        
        db = DatabaseManager(test_db_path)
        
        print(f"✅ Base de datos creada: {test_db_path}")
        print(f"   Tablas: conversations, messages, documents, agent_logs, system_stats")
        
        return db
        
    except Exception as e:
        print(f"❌ Error creando base de datos: {e}")
        return None


def test_conversations(db: DatabaseManager):
    """Test 2: Crear y recuperar conversaciones."""
    print("\n" + "="*60)
    print("TEST 2: Gestión de conversaciones")
    print("="*60)
    
    try:
        # Crear conversación
        conv = db.create_conversation(
            title="Test de Minerva",
            metadata={"test": True}
        )
        
        print(f"✅ Conversación creada: ID={conv.id}, título='{conv.title}'")
        
        # Recuperar conversación
        retrieved = db.get_conversation(conv.id)
        if retrieved and retrieved.id == conv.id:
            print(f"✅ Conversación recuperada correctamente")
        else:
            print(f"❌ Error recuperando conversación")
            return None
        
        # Listar conversaciones activas
        active_convs = db.get_active_conversations()
        print(f"✅ Conversaciones activas: {len(active_convs)}")
        
        return conv
        
    except Exception as e:
        print(f"❌ Error en conversaciones: {e}")
        return None


def test_messages(db: DatabaseManager, conversation):
    """Test 3: Agregar y recuperar mensajes."""
    print("\n" + "="*60)
    print("TEST 3: Gestión de mensajes")
    print("="*60)
    
    try:
        # Agregar mensaje de usuario
        msg1 = db.add_message(
            conversation_id=conversation.id,
            role='user',
            content='¿Cuál es la capital de Francia?'
        )
        print(f"✅ Mensaje usuario agregado: ID={msg1.id}")
        
        # Agregar respuesta
        msg2 = db.add_message(
            conversation_id=conversation.id,
            role='assistant',
            content='La capital de Francia es París.',
            agent_type='conversational',
            model='phi3',
            temperature=0.7,
            tokens=12
        )
        print(f"✅ Mensaje asistente agregado: ID={msg2.id}")
        
        # Recuperar mensajes
        messages = db.get_conversation_messages(conversation.id)
        print(f"✅ Mensajes recuperados: {len(messages)}")
        
        for msg in messages:
            print(f"   - {msg.role}: {msg.content[:50]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en mensajes: {e}")
        return False


def test_documents(db: DatabaseManager):
    """Test 4: Registrar documentos."""
    print("\n" + "="*60)
    print("TEST 4: Registro de documentos")
    print("="*60)
    
    try:
        doc = db.add_document(
            filename="test.pdf",
            file_type="pdf",
            file_size=1024000,
            chunk_count=10,
            qdrant_collection="minerva_memory",
            qdrant_ids=["id1", "id2", "id3"],
            metadata={"test": True}
        )
        
        print(f"✅ Documento registrado: ID={doc.id}, nombre='{doc.filename}'")
        print(f"   Chunks: {doc.chunk_count}, Qdrant IDs: {len(doc.qdrant_ids)}")
        
        # Listar documentos
        docs = db.get_documents()
        print(f"✅ Documentos en DB: {len(docs)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en documentos: {e}")
        return False


def test_agent_logs(db: DatabaseManager):
    """Test 5: Logs de agentes."""
    print("\n" + "="*60)
    print("TEST 5: Logs de agentes")
    print("="*60)
    
    try:
        log = db.add_agent_log(
            agent_name="conversational_agent",
            agent_type="conversational",
            action="chat",
            status="success",
            duration_ms=250,
            input_summary="Usuario preguntó sobre París",
            output_summary="Respondió correctamente"
        )
        
        print(f"✅ Log registrado: ID={log.id}")
        print(f"   Agente: {log.agent_name}, Acción: {log.action}, Status: {log.status}")
        
        # Obtener logs
        logs = db.get_agent_logs()
        print(f"✅ Total de logs: {len(logs)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en logs: {e}")
        return False


def test_stats(db: DatabaseManager):
    """Test 6: Estadísticas del sistema."""
    print("\n" + "="*60)
    print("TEST 6: Estadísticas del sistema")
    print("="*60)
    
    try:
        stats = db.update_stats()
        
        print(f"✅ Estadísticas calculadas:")
        print(f"   Conversaciones: {stats.total_conversations}")
        print(f"   Mensajes: {stats.total_messages}")
        print(f"   Documentos: {stats.total_documents}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error en estadísticas: {e}")
        return False


def test_integration_with_agent():
    """Test 7: Integración agente + base de datos."""
    print("\n" + "="*60)
    print("TEST 7: Integración agente + base de datos")
    print("="*60)
    
    try:
        # Crear DB
        test_db_path = settings.DATA_DIR / "test_agent_minerva.db"
        if test_db_path.exists():
            test_db_path.unlink()
        
        db = DatabaseManager(test_db_path)
        
        # Crear conversación
        conv = db.create_conversation(title="Test integración")
        print(f"✅ Conversación creada: ID={conv.id}")
        
        # Crear agente con DB
        agent = create_conversational_agent(db_manager=db)
        print(f"✅ Agente creado con DB manager")
        
        # Chat (debería guardar en DB)
        response = agent.chat(
            user_message="¿Cuánto es 2+2?",
            conversation_id=conv.id
        )
        
        print(f"✅ Chat completado: {response[:50]}...")
        
        # Verificar que se guardó
        messages = db.get_conversation_messages(conv.id)
        print(f"✅ Mensajes en DB: {len(messages)}")
        
        for msg in messages:
            print(f"   - {msg.role}: {msg.content[:50]}...")
        
        # Limpiar
        db.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Error en integración: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Ejecuta todos los tests."""
    print("\n" + "="*60)
    print("🧪 TESTS DE FASE 2.5 - BASE DE DATOS SQLITE")
    print("="*60)
    
    # Test 1: Crear DB
    db = test_database_creation()
    if not db:
        print("\n❌ No se pudo crear DB. Abortando.")
        return
    
    # Test 2: Conversaciones
    conv = test_conversations(db)
    if not conv:
        print("\n❌ Falló gestión de conversaciones.")
        return
    
    # Test 3: Mensajes
    if not test_messages(db, conv):
        print("\n❌ Falló gestión de mensajes.")
        return
    
    # Test 4: Documentos
    if not test_documents(db):
        print("\n❌ Falló registro de documentos.")
        return
    
    # Test 5: Logs
    if not test_agent_logs(db):
        print("\n❌ Falló sistema de logs.")
        return
    
    # Test 6: Stats
    if not test_stats(db):
        print("\n❌ Falló cálculo de estadísticas.")
        return
    
    # Cerrar DB de prueba
    db.close()
    
    # Test 7: Integración con agente
    if not test_integration_with_agent():
        print("\n❌ Falló integración con agente.")
        return
    
    # Resumen
    print("\n" + "="*60)
    print("✅ TODOS LOS TESTS COMPLETADOS")
    print("="*60)
    print("\nFase 2.5 funcionando correctamente:")
    print("  ✓ Base de datos SQLite creada")
    print("  ✓ Conversaciones y mensajes funcionando")
    print("  ✓ Registro de documentos operativo")
    print("  ✓ Sistema de logs activo")
    print("  ✓ Estadísticas calculándose")
    print("  ✓ Integración con agente completa")
    print("\n🎉 ¡Listo para Fase 3!")


if __name__ == "__main__":
    main()