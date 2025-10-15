# src/ui/chat_interface.py - Interfaz de chat con Gradio
"""
Interfaz de chat para Minerva usando Gradio.
Proporciona una UI amigable para interactuar con el asistente.
"""

import gradio as gr
from datetime import datetime
from typing import List, Tuple
import logging

from src.router.intelligent_router import IntelligentRouter
from config.settings import settings

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Inicializar router global
router = None
# Conversation ID para la sesión actual
current_conversation_id = None


def initialize_router():
    """Inicializa el router de manera lazy (solo cuando se necesita)."""
    global router
    if router is None:
        logger.info("Inicializando router inteligente...")
        
        # Importar todos los componentes necesarios
        from src.embeddings import EmbeddingService
        from src.memory import VectorMemory
        from src.database import DatabaseManager
        from src.processing.indexer import DocumentIndexer
        from src.agents.conversational import ConversationalAgent
        from src.agents.knowledge import KnowledgeAgent
        from config.settings import settings
        
        # === ORDEN CORRECTO DE INICIALIZACIÓN ===
        
        # 1. Embedding Service (necesita model_name)
        logger.info("1/7 Inicializando Embedding Service...")
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL
        )
        
        # 2. Vector Memory / Qdrant (necesita path, collection_name, vector_size)
        logger.info("2/7 Inicializando Vector Memory (Qdrant)...")
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        # 3. Database Manager / SQLite (necesita db_path)
        logger.info("3/7 Inicializando Database Manager...")
        db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
        
        # 4. Document Indexer (necesita vector_memory, db_manager, embedding_service)
        logger.info("4/7 Inicializando Document Indexer...")
        indexer = DocumentIndexer(
            vector_memory=vector_memory,
            db_manager=db_manager,
            embedding_service=embedding_service,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        # 5. Conversational Agent (todos opcionales, pero pasamos db_manager)
        logger.info("5/7 Inicializando Conversational Agent...")
        conversational_agent = ConversationalAgent(
            model_name=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            db_manager=db_manager
        )
        
        # 6. Knowledge Agent (necesita db_manager e indexer)
        logger.info("6/7 Inicializando Knowledge Agent...")
        knowledge_agent = KnowledgeAgent(
            model_name=settings.OLLAMA_MODEL,
            temperature=0.3,  # Más preciso para conocimiento
            db_manager=db_manager,
            indexer=indexer
        )
        
        # 7. Router (necesita conversational_agent, knowledge_agent, indexer)
        logger.info("7/7 Inicializando Router...")
        router = IntelligentRouter(
            conversational_agent=conversational_agent,
            knowledge_agent=knowledge_agent,
            indexer=indexer,
            knowledge_threshold=settings.KNOWLEDGE_THRESHOLD
        )
        
        logger.info("✅ Router y todos los componentes inicializados correctamente")
        
        # Crear conversación inicial automáticamente
        if current_conversation_id is None:
            try:
                from datetime import datetime
                conv = router.conversational_agent.db_manager.create_conversation(
                    title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    metadata={'source': 'gradio_ui', 'auto_created': True}
                )
                globals()['current_conversation_id'] = conv.id
                logger.info(f"✅ Conversación inicial creada: ID={conv.id}")
            except Exception as e:
                logger.error(f"Error creando conversación inicial: {e}")
    
    return router


def format_response_with_metadata(response: str, metadata: dict) -> str:
    """
    Formatea la respuesta con metadata visual.
    
    Args:
        response: Respuesta del agente
        metadata: Diccionario con información adicional
    
    Returns:
        String formateado con markdown
    """
    formatted = response + "\n\n---\n\n"
    
    # Información del agente
    agent_type = metadata.get('agent_type', 'unknown')
    agent_emoji = {
        'conversational': '💬',
        'knowledge': '📚',
        'web': '🌐'
    }
    
    formatted += f"{agent_emoji.get(agent_type, '🤖')} **Agente**: {agent_type.title()}\n\n"
    
    # Nivel de confianza
    confidence = metadata.get('confidence_level')
    if confidence:
        confidence_emoji = {
            'Alta': '🟢',
            'Media': '🟡',
            'Baja': '🔴'
        }
        formatted += f"{confidence_emoji.get(confidence, '⚪')} **Confianza**: {confidence}\n\n"
    
    # Fuentes
    sources = metadata.get('sources', [])
    if sources:
        formatted += "📎 **Fuentes**:\n"
        for i, source in enumerate(sources[:3], 1):  # Máximo 3 fuentes
            formatted += f"{i}. {source}\n"
        formatted += "\n"
    
    return formatted


def export_conversation(history: List[Tuple[str, str]]) -> str:
    """
    Exporta la conversación a formato texto.
    
    Args:
        history: Historial de la conversación
    
    Returns:
        String con la conversación formateada
    """
    if not history:
        return "No hay conversación para exportar."
    
    lines = ["=" * 60, "CONVERSACIÓN CON MINERVA", "=" * 60, ""]
    
    for i, (user_msg, bot_msg) in enumerate(history, 1):
        lines.append(f"[Mensaje #{i}]")
        lines.append(f"Usuario: {user_msg}")
        
        # Limpiar el mensaje del bot (quitar metadata visible)
        clean_bot_msg = bot_msg.split("---")[0].strip()  # Solo la respuesta, sin metadata
        lines.append(f"\nMinerva: {clean_bot_msg}")
        lines.append("\n" + "-" * 60 + "\n")
    
    return "\n".join(lines)


def initialize_conversation():
    """Inicializa una nueva conversación en la base de datos."""
    global current_conversation_id
    
    try:
        current_router = initialize_router()
        
        # Crear nueva conversación en la DB
        from datetime import datetime
        conv = current_router.conversational_agent.db_manager.create_conversation(
            title=f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            metadata={'source': 'gradio_ui'}
        )
        current_conversation_id = conv.id
        
        logger.info(f"✅ Nueva conversación creada: ID={current_conversation_id}")
        return current_conversation_id
        
    except Exception as e:
        logger.error(f"❌ Error creando conversación: {e}")
        import traceback
        traceback.print_exc()
        return None


def chat_function(message: str, history: List[Tuple[str, str]]) -> Tuple[List[Tuple[str, str]], str]:
    """
    Función principal del chat que procesa mensajes.
    
    Args:
        message: Mensaje del usuario
        history: Historial de la conversación
    
    Returns:
        Tupla de (nuevo_historial, string_vacío)
    """
    if not message or not message.strip():
        return history, ""
    
    try:
        # Inicializar router si no existe
        current_router = initialize_router()
        
        # Asegurarse de que existe una conversación
        global current_conversation_id
        if current_conversation_id is None:
            initialize_conversation()
        
        # Procesar mensaje con conversation_id
        logger.info(f"Usuario: {message}")
        response_data = current_router.route(
            user_message=message,
            conversation_id=current_conversation_id
        )
        
        # Debug: ver qué retorna el router
        logger.info(f"Router retornó: {type(response_data)}")
        logger.info(f"Keys en response: {response_data.keys() if isinstance(response_data, dict) else 'No es dict'}")
        
        # Extraer respuesta y metadata de forma robusta
        if isinstance(response_data, dict):
            # El router retorna 'answer', no 'response'
            response_text = (
                response_data.get('answer') or 
                response_data.get('response') or 
                response_data.get('output', 'Lo siento, no pude generar una respuesta.')
            )
            
            # Construir metadata
            metadata = {
                'agent_type': response_data.get('agent_used', 'unknown'),
                'confidence_level': response_data.get('confidence', ''),
                'sources': response_data.get('sources', []),
                'search_score': response_data.get('search_score', 0)
            }
        else:
            # Si no es un dict, intentar usar como string directo
            response_text = str(response_data)
            metadata = {'agent_type': 'unknown'}
        
        # Formatear respuesta
        formatted_response = format_response_with_metadata(response_text, metadata)
        
        # Agregar al historial
        history.append((message, formatted_response))
        
        logger.info(f"Minerva ({metadata.get('agent_type', 'unknown')}): Respuesta enviada")
        
        return history, ""
        
    except Exception as e:
        logger.error(f"Error en chat: {e}", exc_info=True)
        error_msg = f"❌ **Error**: Lo siento, ocurrió un error al procesar tu mensaje.\n\n```\n{str(e)}\n```"
        history.append((message, error_msg))
        return history, ""


def clear_chat() -> Tuple[List, str]:
    """Limpia el historial del chat y crea nueva conversación."""
    global current_conversation_id
    
    # Crear nueva conversación
    initialize_conversation()
    
    logger.info("Chat limpiado y nueva conversación creada")
    return [], ""


def get_system_info() -> str:
    """Obtiene información del sistema."""
    try:
        current_router = initialize_router()
        
        # Obtener estadísticas
        stats = {
            'model': settings.OLLAMA_MODEL,
            'embedding_model': settings.EMBEDDING_MODEL,
            'collection': settings.QDRANT_COLLECTION_NAME,
            'temperature': settings.OLLAMA_TEMPERATURE,
            'threshold': settings.KNOWLEDGE_THRESHOLD
        }
        
        info = "## ⚙️ Configuración Actual\n\n"
        info += f"**Modelo LLM**: {stats['model']}\n\n"
        info += f"**Modelo Embeddings**: {stats['embedding_model']}\n\n"
        info += f"**Colección**: {stats['collection']}\n\n"
        info += f"**Temperatura**: {stats['temperature']}\n\n"
        info += f"**Umbral de conocimiento**: {stats['threshold']}\n\n"
        
        return info
    except Exception as e:
        return f"❌ Error al obtener información: {e}"


def create_interface() -> gr.Blocks:
    """
    Crea y configura la interfaz de Gradio.
    
    Returns:
        Objeto gr.Blocks configurado
    """
    
    # Tema personalizado
    theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
        neutral_hue="slate",
        font=["Inter", "sans-serif"]
    )
    
    # Crear interfaz
    with gr.Blocks(
        theme=theme,
        title="Minerva - Asistente Personal Local",
        css="""
        .gradio-container {
            max-width: 1200px !important;
        }
        .chat-message {
            padding: 10px;
            border-radius: 8px;
        }
        """
    ) as interface:
        
        # Header
        gr.Markdown(
            """
            # 🧠 Minerva
            ### Tu Asistente Personal Local con RAG
            
            ---
            """
        )
        
        # Layout principal
        with gr.Row():
            # Columna principal - Chat
            with gr.Column(scale=3):
                chatbot = gr.Chatbot(
                    label="Conversación",
                    height=500,
                    show_label=True,
                    bubble_full_width=False
                    # avatar_images removido temporalmente por compatibilidad
                )
                
                with gr.Row():
                    msg_input = gr.Textbox(
                        label="Tu mensaje",
                        placeholder="Escribe tu mensaje aquí... (Shift+Enter para enviar)",
                        lines=2,
                        scale=4,
                        show_label=False
                    )
                    send_btn = gr.Button("📤 Enviar", scale=1, variant="primary")
                
                with gr.Row():
                    clear_btn = gr.Button("🗑️ Limpiar chat", size="sm")
                    export_btn = gr.Button("📋 Copiar conversación", size="sm", variant="secondary")
                
                # Área de texto oculta para la conversación exportada
                exported_text = gr.Textbox(
                    label="Conversación exportada (selecciona todo y copia)",
                    lines=10,
                    max_lines=20,
                    visible=False,
                    interactive=True
                )
                    
            
            # Columna lateral - Info y controles
            with gr.Column(scale=1):
                gr.Markdown("## 📊 Panel de Control")
                
                # Botón de info del sistema
                info_btn = gr.Button("⚙️ Ver Configuración", size="sm")
                system_info = gr.Markdown("", visible=False)
                
                gr.Markdown("---")
                
                # Información de uso
                gr.Markdown(
                    """
                    ### 💡 Consejos
                    
                    **Conversación casual:**
                    - "Hola, ¿cómo estás?"
                    - "Cuéntame un chiste"
                    
                    **Consultas sobre documentos:**
                    - "¿Qué dice el documento sobre...?"
                    - "Resume el contenido de..."
                    
                    **Estado:**
                    - 🟢 Sistema funcionando
                    - 💬 Agente conversacional
                    - 📚 Agente de conocimiento
                    - 💾 Conversación persistente
                    
                    ---
                    
                    ### 🔒 Privacidad
                    Todo se procesa localmente.
                    Sin internet. Sin tracking.
                    """
                )
        
        # Footer
        gr.Markdown(
            """
            ---
            <div style='text-align: center; color: #666; font-size: 0.9em;'>
                Minerva v1.0 | Fase 5 | Powered by Ollama + Phi-3 + Qdrant
            </div>
            """
        )
        
        # Event handlers
        
        # Crear conversación al cargar la interfaz
        def init_on_load():
            initialize_conversation()
            return None
        
        interface.load(
            fn=init_on_load,
            inputs=None,
            outputs=None
        )
        
        # Enviar mensaje con botón
        send_btn.click(
            fn=chat_function,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input],
            api_name="chat"
        )
        
        # Enviar mensaje con Enter
        msg_input.submit(
            fn=chat_function,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, msg_input]
        )
        
        # Limpiar chat
        clear_btn.click(
            fn=clear_chat,
            inputs=None,
            outputs=[chatbot, msg_input]
        )
        
        # Exportar conversación
        def show_export(history):
            text = export_conversation(history)
            return gr.Textbox(value=text, visible=True)
        
        export_btn.click(
            fn=show_export,
            inputs=chatbot,
            outputs=exported_text
        )
        
        # Mostrar info del sistema
        def toggle_info():
            info = get_system_info()
            return gr.Markdown(value=info, visible=True)
        
        info_btn.click(
            fn=toggle_info,
            inputs=None,
            outputs=system_info
        )
    
    return interface


# Para testing directo
if __name__ == "__main__":
    print("Lanzando interfaz de prueba...")
    interface = create_interface()
    interface.launch(server_port=7860, share=False)