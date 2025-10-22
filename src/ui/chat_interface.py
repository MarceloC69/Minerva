# src/ui/chat_interface.py - v5.0.0 - Con gestión de hechos
"""
Interfaz de chat de Minerva con memoria persistente REAL.
Incluye tab para ver y gestionar hechos almacenados.
"""

import gradio as gr
import logging
from datetime import datetime
from typing import Tuple

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger("src.ui.chat_interface")

# Variable global para el crew
crew = None
current_conversation_id = None

def initialize_crew():
    """Inicializa MinervaCrew con memoria LangChain + Hechos."""
    global crew
    
    if crew is None:
        logger.info("🚀 Inicializando MinervaCrew con MEMORIA PERSISTENTE...")
        
        from src.embeddings import EmbeddingService
        from src.memory import VectorMemory
        from src.database import DatabaseManager
        from src.processing.indexer import DocumentIndexer
        from src.agents.conversational import ConversationalAgent
        from src.agents.knowledge import KnowledgeAgent
        from src.agents.web import WebAgent
        from config.settings import settings
        
        # 1. Embedding Service
        logger.info("1/7 Embedding Service...")
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL
        )
        
        # 2. Vector Memory (Qdrant)
        logger.info("2/7 Vector Memory...")
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        # 3. Database Manager
        logger.info("3/7 Database Manager...")
        db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
        
        # 4. Document Indexer
        logger.info("4/7 Document Indexer...")
        indexer = DocumentIndexer(
            vector_memory=vector_memory,
            db_manager=db_manager,
            embedding_service=embedding_service,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        # 5. Conversational Agent CON MEMORIA
        logger.info("5/7 Conversational Agent (LangChain + Hechos)...")
        conversational_agent = ConversationalAgent(
            model_name=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            db_manager=db_manager,
            embedding_service=embedding_service,
            vector_memory=vector_memory,
            extraction_interval=1
        )
        
        # 6. Knowledge Agent
        logger.info("6/7 Knowledge Agent...")
        knowledge_agent = KnowledgeAgent(
            model_name=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            db_manager=db_manager,
            indexer=indexer
        )
        
        # 7. Web Agent
        logger.info("7/7 Web Agent...")
        web_agent = WebAgent(
            model_name=settings.OLLAMA_MODEL,
            temperature=settings.OLLAMA_TEMPERATURE,
            db_manager=db_manager
        )
        
        # 8. MinervaCrew
        logger.info("Creando MinervaCrew...")
        from src.crew import MinervaCrew
        crew = MinervaCrew(
            conversational_agent=conversational_agent,
            knowledge_agent=knowledge_agent,
            web_agent=web_agent,
            db_manager=db_manager,
            indexer=indexer,
            memory_service=None
        )
        
        logger.info("✅ MinervaCrew con memoria persistente listo")
    
    return crew


def get_loaded_prompts_info():
    """Obtiene información de los prompts cargados."""
    global crew
    
    try:
        if crew is None:
            return "ℹ️ Iniciando..."
        
        from src.database.prompt_manager import PromptManager
        
        pm = PromptManager(crew.db_manager)
        
        info = ""
        
        # Conversational
        try:
            hist = pm.get_prompt_history('conversational', 'system_prompt', limit=1)
            if hist:
                info += f"**conversational/**\n"
                info += f"system_prompt v{hist[0].version}\n\n"
        except:
            pass
        
        # Fact Extractor
        try:
            hist = pm.get_prompt_history('fact_extractor', 'extraction_prompt', limit=1)
            if hist:
                info += f"**fact_extractor/**\n"
                info += f"extraction_prompt v{hist[0].version}\n\n"
        except:
            pass
        
        # Router
        try:
            hist = pm.get_prompt_history('router', 'classification_prompt', limit=1)
            if hist:
                info += f"**router/**\n"
                info += f"classification_prompt v{hist[0].version}\n\n"
        except:
            pass
        
        return info if info else "ℹ️ Sin prompts"
        
    except Exception as e:
        logger.error(f"Error obteniendo prompts: {e}")
        return "⚠️ Error"


def initialize_conversation():
    """Crea nueva conversación."""
    global current_conversation_id, crew
    
    try:
        crew = initialize_crew()
        
        previous_conversation_id = current_conversation_id
        
        conv = crew.db_manager.create_conversation(
            title=f"Conversación {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        current_conversation_id = conv.id
        
        logger.info(f"✅ Nueva conversación: ID {current_conversation_id}")
        
        if previous_conversation_id:
            logger.info(f"📋 Conversación anterior: ID {previous_conversation_id}")
        
        return []
    
    except Exception as e:
        logger.error(f"❌ Error creando conversación: {e}")
        import traceback
        traceback.print_exc()
        return []


def chat_function(message: str, history):
    """Procesa mensaje con memoria persistente."""
    global current_conversation_id, crew
    
    try:
        logger.info(f"Usuario: {message}")
        
        crew = initialize_crew()
        
        if current_conversation_id is None:
            initialize_conversation()
        
        response_data = crew.route(
            user_message=message,
            conversation_id=current_conversation_id
        )
        
        answer = response_data.get('answer', 'Lo siento, no pude generar una respuesta.')
        agent_used = response_data.get('agent_used', 'unknown')
        confidence = response_data.get('confidence', 'Media')
        
        agent_icons = {
            'conversational': '💬',
            'knowledge': '📚',
            'web': '🌐',
            'memory': '🧠'
        }
        
        icon = agent_icons.get(agent_used, '🤖')
        response_with_meta = f"{answer}\n\n---\n*{icon} {agent_used.title()} • Confianza: {confidence}*"
        
        return response_with_meta
    
    except Exception as e:
        logger.error(f"❌ Error en chat: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}"


def export_conversation():
    """Exporta la conversación actual."""
    global current_conversation_id, crew
    
    if current_conversation_id is None:
        return "No hay conversación activa."
    
    try:
        if crew is None:
            crew = initialize_crew()
        
        from src.memory.langchain_memory import LangChainMemoryWrapper
        from config.settings import settings
        
        langchain_mem = LangChainMemoryWrapper(
            db_path=str(settings.SQLITE_PATH),
            conversation_id=current_conversation_id
        )
        
        messages = langchain_mem.get_messages()
        
        if not messages:
            return "La conversación está vacía."
        
        export_text = f"=== Conversación Minerva ===\n"
        export_text += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_text += f"ID: {current_conversation_id}\n"
        export_text += "=" * 50 + "\n\n"
        
        for msg in messages:
            if hasattr(msg, 'type'):
                role = "Usuario" if msg.type == "human" else "Minerva"
            else:
                role = "Usuario" if msg.__class__.__name__ == "HumanMessage" else "Minerva"
            
            export_text += f"{role}: {msg.content}\n\n"
        
        return export_text
    
    except Exception as e:
        logger.error(f"❌ Error exportando: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"


# ==================== GESTIÓN DE HECHOS ====================

def load_all_facts() -> str:
    """Carga todos los hechos almacenados en formato HTML."""
    try:
        from src.embeddings import EmbeddingService
        from src.memory.vector_store import VectorMemory
        from config.settings import settings
        
        embedding_service = EmbeddingService(model_name=settings.EMBEDDING_MODEL)
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        # Obtener todos los puntos
        scroll_result = vector_memory.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        points = scroll_result[0]
        
        # Filtrar solo hechos
        facts = []
        for point in points:
            payload = point.payload or {}
            if payload.get('type') == 'fact':
                text = payload.get('text', '')
                # Limpiar prefijos de categoría
                for prefix in ['[personal] ', '[professional] ', '[personal_age] ', '[hobby] ']:
                    text = text.replace(prefix, '')
                
                facts.append({
                    'id': str(point.id),
                    'text': text,
                    'category': payload.get('category', 'unknown'),
                    'created_at': payload.get('created_at', 'N/A')
                })
        
        if not facts:
            return "<p style='color: #666; text-align: center; padding: 20px;'>📭 No hay hechos almacenados</p>"
        
        # HTML con cards de hechos
        html = f"""
        <style>
            .facts-container {{
                max-width: 100%;
                margin: 10px 0;
            }}
            .facts-header {{
                background: #f8f9fa;
                padding: 10px 15px;
                border-radius: 8px;
                margin-bottom: 15px;
                font-weight: 600;
            }}
            .fact-card {{
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
                background: white;
                transition: all 0.2s;
            }}
            .fact-card:hover {{
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}
            .fact-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }}
            .fact-number {{
                font-weight: 600;
                color: #666;
                font-size: 0.9em;
            }}
            .fact-category {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                background: #e9ecef;
                color: #495057;
            }}
            .fact-text {{
                font-size: 1.1em;
                margin: 10px 0;
                line-height: 1.5;
            }}
            .fact-meta {{
                font-size: 0.85em;
                color: #6c757d;
                margin-top: 8px;
            }}
        </style>
        <div class='facts-container'>
            <div class='facts-header'>
                📊 Total de hechos almacenados: {len(facts)}
            </div>
        """
        
        for i, fact in enumerate(facts, 1):
            html += f"""
            <div class='fact-card'>
                <div class='fact-header'>
                    <span class='fact-number'>#{i}</span>
                    <span class='fact-category'>{fact['category']}</span>
                </div>
                <div class='fact-text'>{fact['text']}</div>
                <div class='fact-meta'>
                    📅 Creado: {fact['created_at'][:19] if len(fact['created_at']) > 19 else fact['created_at']}
                </div>
            </div>
            """
        
        html += "</div>"
        return html
        
    except Exception as e:
        logger.error(f"Error cargando hechos: {e}")
        import traceback
        traceback.print_exc()
        return f"<p style='color: red;'>❌ Error: {str(e)}</p>"


def get_fact_ids_list() -> list:
    """Obtiene lista de IDs de hechos para el dropdown."""
    try:
        from src.memory.vector_store import VectorMemory
        from config.settings import settings
        
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        scroll_result = vector_memory.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=100,
            with_payload=True,
            with_vectors=False
        )
        
        fact_options = []
        for point in scroll_result[0]:
            payload = point.payload or {}
            if payload.get('type') == 'fact':
                text = payload.get('text', '')
                for prefix in ['[personal] ', '[professional] ', '[personal_age] ']:
                    text = text.replace(prefix, '')
                # Limitar texto a 80 caracteres
                display_text = text[:80] + "..." if len(text) > 80 else text
                fact_options.append((display_text, str(point.id)))
        
        return fact_options if fact_options else [("No hay hechos", "")]
        
    except Exception as e:
        logger.error(f"Error obteniendo IDs: {e}")
        return [("Error cargando", "")]


def delete_fact(fact_id: str) -> Tuple[str, str]:
    """Elimina un hecho por su ID."""
    try:
        if not fact_id:
            return "⚠️ Selecciona un hecho para eliminar", load_all_facts()
        
        from src.memory.vector_store import VectorMemory
        from config.settings import settings
        
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        # Eliminar el punto
        vector_memory.client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=[fact_id]
        )
        
        return "✅ Hecho eliminado correctamente", load_all_facts()
        
    except Exception as e:
        logger.error(f"Error eliminando hecho: {e}")
        return f"❌ Error: {str(e)}", load_all_facts()


def clear_all_facts() -> Tuple[str, str]:
    """Elimina TODOS los hechos (PELIGROSO)."""
    try:
        from src.memory.vector_store import VectorMemory
        from config.settings import settings
        
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        # Obtener todos los IDs de hechos
        scroll_result = vector_memory.client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=1000,
            with_payload=True,
            with_vectors=False
        )
        
        fact_ids = []
        for point in scroll_result[0]:
            payload = point.payload or {}
            if payload.get('type') == 'fact':
                fact_ids.append(str(point.id))
        
        if fact_ids:
            vector_memory.client.delete(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                points_selector=fact_ids
            )
            
            return f"✅ Se eliminaron {len(fact_ids)} hechos", load_all_facts()
        else:
            return "⚠️ No había hechos para eliminar", load_all_facts()
        
    except Exception as e:
        logger.error(f"Error limpiando hechos: {e}")
        return f"❌ Error: {str(e)}", load_all_facts()


def create_interface():
    """Crea interfaz Gradio con tab de hechos."""
    
    with gr.Blocks(title="Minerva Chat", theme=gr.themes.Soft()) as interface:
        
        gr.Markdown("# 🧠 Minerva - Asistente con Memoria Persistente")
        
        with gr.Tabs():
            
            # ============= TAB 1: CHAT =============
            with gr.Tab("💬 Chat"):
                with gr.Row():
                    with gr.Column(scale=4):
                        chatbot = gr.Chatbot(
                            height=400,
                            show_label=False,
                            avatar_images=(None, "🧠")
                        )
                        
                        with gr.Row():
                            msg_input = gr.Textbox(
                                placeholder="Escribe tu mensaje aquí...",
                                show_label=False,
                                scale=4
                            )
                            submit_btn = gr.Button("Enviar", variant="primary", scale=1)
                        
                        with gr.Row():
                            clear_btn = gr.Button("🗑️ Nueva Conversación", size="sm")
                            export_btn = gr.Button("💾 Exportar", size="sm")
                    
                    with gr.Column(scale=1):
                        gr.Markdown("### ℹ️ Sistema")
                        
                        prompts_info = gr.Markdown(
                            value="ℹ️ Iniciando...",
                            label="Prompts"
                        )
                        
                        refresh_prompts_btn = gr.Button("🔄 Actualizar", size="sm")
                        
                        gr.Markdown("\n**Modelo:** Phi3\n**Memoria:** Activa")
                        
                        export_output = gr.Textbox(
                            label="Exportar",
                            lines=10,
                            visible=False
                        )
                
                # Event handlers
                def user_message(message, history):
                    return "", history + [[message, None]]
                
                def bot_response(history):
                    if not history or history[-1][1] is not None:
                        return history, get_loaded_prompts_info()
                    
                    user_msg = history[-1][0]
                    bot_msg = chat_function(user_msg, history[:-1])
                    history[-1][1] = bot_msg
                    
                    return history, get_loaded_prompts_info()
                
                msg_input.submit(
                    user_message,
                    [msg_input, chatbot],
                    [msg_input, chatbot],
                    queue=False
                ).then(
                    bot_response,
                    chatbot,
                    [chatbot, prompts_info]
                )
                
                submit_btn.click(
                    user_message,
                    [msg_input, chatbot],
                    [msg_input, chatbot],
                    queue=False
                ).then(
                    bot_response,
                    chatbot,
                    [chatbot, prompts_info]
                )
                
                clear_btn.click(
                    initialize_conversation,
                    None,
                    chatbot,
                    queue=False
                ).then(
                    lambda: get_loaded_prompts_info(),
                    None,
                    prompts_info
                )
                
                refresh_prompts_btn.click(
                    get_loaded_prompts_info,
                    None,
                    prompts_info
                )
                
                def show_export():
                    text = export_conversation()
                    return gr.update(visible=True, value=text)
                
                export_btn.click(
                    show_export,
                    None,
                    export_output
                )
            
            # ============= TAB 2: HECHOS =============
            with gr.Tab("🧠 Hechos Almacenados"):
                
                gr.Markdown("""
                ### Gestión de Hechos
                
                Aquí puedes ver todos los hechos que Minerva ha aprendido sobre ti.
                Los hechos se extraen automáticamente de las conversaciones.
                """)
                
                with gr.Row():
                    refresh_facts_btn = gr.Button("🔄 Recargar Hechos", variant="primary", scale=1)
                    clear_all_btn = gr.Button("🗑️ Eliminar TODOS los Hechos", variant="stop", scale=1)
                
                facts_result = gr.Markdown("")
                
                facts_display = gr.HTML(
                    value=load_all_facts(),
                    label="Hechos"
                )
                
                gr.Markdown("---")
                gr.Markdown("### Eliminar Hecho Individual")
                
                with gr.Row():
                    fact_selector = gr.Dropdown(
                        choices=[],
                        label="Selecciona un hecho para eliminar",
                        scale=3
                    )
                    delete_fact_btn = gr.Button("🗑️ Eliminar", variant="stop", scale=1)
                
                delete_result = gr.Markdown("")
                
                # Eventos
                def refresh_facts_and_dropdown():
                    facts_html = load_all_facts()
                    fact_options = get_fact_ids_list()
                    return facts_html, gr.Dropdown(choices=fact_options)
                
                refresh_facts_btn.click(
                    refresh_facts_and_dropdown,
                    None,
                    [facts_display, fact_selector]
                )
                
                delete_fact_btn.click(
                    delete_fact,
                    inputs=fact_selector,
                    outputs=[delete_result, facts_display]
                ).then(
                    refresh_facts_and_dropdown,
                    None,
                    [facts_display, fact_selector]
                )
                
                clear_all_btn.click(
                    clear_all_facts,
                    None,
                    [facts_result, facts_display]
                ).then(
                    refresh_facts_and_dropdown,
                    None,
                    [facts_display, fact_selector]
                )
                
                # Cargar dropdown inicial
                interface.load(
                    get_fact_ids_list,
                    None,
                    fact_selector
                )
        
        gr.Markdown(
            """
            ---
            <div style='text-align: center; color: #666; font-size: 0.9em;'>
                🧠 <strong>Minerva</strong> - Tu asistente con memoria persistente real
            </div>
            """
        )
    
    return interface