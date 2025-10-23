# src/ui/chat_interface.py - v7.3.0 COMPLETO - Fix delete_memory + mejor logging
"""
Interfaz de chat de Minerva con memoria persistente (mem0).
Versión completa con todas las funcionalidades.

FIXES v7.3.0:
- ✅ Fix función delete_memory (manejo robusto de IDs)
- ✅ Mejor logging para debugging de mem0
- ✅ Validación de memoria antes de eliminar
- ✅ Manejo de errores más detallado
- ✅ (Mantiene todos los fixes de v7.2.0)
"""

import gradio as gr
import logging
import os
from datetime import datetime
from typing import Tuple, List

# 🔧 FIX CUDA: Forzar CPU para mem0 (evitar error con GTX 1050)
os.environ['CUDA_VISIBLE_DEVICES'] = ''  # Deshabilita CUDA
os.environ['TORCH_USE_CUDA_DSA'] = '0'

logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger("src.ui.chat_interface")

# Variables globales
crew = None
current_conversation_id = None


def initialize_crew():
    """Inicializa MinervaCrew con CrewAI + mem0 (CPU-only)."""
    global crew
    
    if crew is None:
        logger.info("🚀 Inicializando MinervaCrew (CrewAI + mem0 en CPU)...")
        
        from src.database import DatabaseManager
        from src.embeddings import EmbeddingService
        from src.memory.vector_store import VectorMemory
        from src.memory.mem0_wrapper import Mem0Wrapper
        from src.processing.indexer import DocumentIndexer
        from src.agents.conversational import ConversationalAgent
        from src.agents.knowledge import KnowledgeAgent
        from src.agents.web import WebAgent
        from src.crew.minerva_crew import MinervaCrew
        from config.settings import settings
        
        # Componentes
        db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
        
        embedding_service = EmbeddingService(
            model_name=settings.EMBEDDING_MODEL
        )
        
        vector_memory = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name="knowledge_base",
            vector_size=settings.EMBEDDING_DIM
        )
        
        indexer = DocumentIndexer(
            vector_memory=vector_memory,
            db_manager=db_manager,
            embedding_service=embedding_service,
            chunk_size=settings.CHUNK_SIZE,
            chunk_overlap=settings.CHUNK_OVERLAP
        )
        
        # Inicializar mem0 (en CPU)
        try:
            logger.info("🧠 Inicializando mem0 en CPU (CUDA deshabilitado)...")
            memory_service = Mem0Wrapper(user_id="marcelo", organization_id="minerva")
            logger.info("✅ mem0 inicializado correctamente en CPU")
        except Exception as e:
            logger.error(f"❌ Error inicializando mem0: {e}")
            import traceback
            traceback.print_exc()
            memory_service = None
        
        # Agentes
        conversational_agent = ConversationalAgent(
            model_name=settings.OLLAMA_MODEL,
            db_manager=db_manager,
            memory_service=memory_service
        )
        
        knowledge_agent = KnowledgeAgent(
            model_name=settings.OLLAMA_MODEL,
            db_manager=db_manager,
            indexer=indexer
        )
        
        web_agent = WebAgent(
            model_name=settings.OLLAMA_MODEL,
            db_manager=db_manager
        )
        
        # MinervaCrew
        crew = MinervaCrew(
            conversational_agent=conversational_agent,
            knowledge_agent=knowledge_agent,
            web_agent=web_agent,
            db_manager=db_manager,
            indexer=indexer,
            memory_service=memory_service
        )
        
        logger.info("✅ MinervaCrew listo")
    
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
        
        # Knowledge
        try:
            hist = pm.get_prompt_history('knowledge', 'system_prompt', limit=1)
            if hist:
                info += f"**knowledge/**\n"
                info += f"system_prompt v{hist[0].version}\n\n"
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
        
        conv = crew.db_manager.create_conversation(
            title=f"Conversación {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        current_conversation_id = conv.id
        
        logger.info(f"✅ Nueva conversación: ID {current_conversation_id}")
        
        return []
    
    except Exception as e:
        logger.error(f"❌ Error creando conversación: {e}")
        import traceback
        traceback.print_exc()
        return []


def chat_function(message: str, history):
    """Procesa mensaje con CrewAI + mem0."""
    global current_conversation_id, crew
    
    try:
        logger.info(f"Usuario: {message}")
        
        crew = initialize_crew()
        
        if current_conversation_id is None:
            initialize_conversation()
        
        # Procesar con MinervaCrew (CrewAI + mem0)
        response_data = crew.route(
            user_message=message,
            conversation_id=current_conversation_id
        )
        
        answer = response_data.get('answer', 'Lo siento, no pude generar una respuesta.')
        agent_used = response_data.get('agent', 'unknown')
        
        agent_icons = {
            'conversational': '💬',
            'knowledge': '📚',
            'web': '🌐',
            'memory': '🧠',
            'source_retrieval': '🔗'
        }
        
        icon = agent_icons.get(agent_used, '🤖')
        response_with_meta = f"{answer}\n\n---\n*{icon} {agent_used.title()}*"
        
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
        crew = initialize_crew()
        
        # Usar LangChain memory
        from src.memory.langchain_memory import LangChainMemoryWrapper
        from config.settings import settings
        
        memory = LangChainMemoryWrapper(
            db_path=str(settings.SQLITE_PATH),
            conversation_id=current_conversation_id
        )
        
        messages = memory.get_messages()  # Retorna lista de dicts
        
        if not messages:
            return "Conversación vacía."
        
        export_text = f"=== Conversación Minerva ===\n"
        export_text += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_text += f"ID: {current_conversation_id}\n"
        export_text += "=" * 50 + "\n\n"
        
        # messages son dicts con 'role' y 'content'
        for msg in messages:
            role = "Usuario" if msg['role'] == 'user' else "Minerva"
            export_text += f"{role}: {msg['content']}\n\n"
        
        return export_text
    
    except Exception as e:
        logger.error(f"❌ Error exportando: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)}"


# ==================== GESTIÓN DE MEMORIA (mem0) ====================

def load_all_memories() -> str:
    """
    Carga todas las memorias de mem0.
    
    ESTRUCTURA REAL de mem0.get_all():
    {
        'results': [
            {
                'id': 'uuid-string',
                'memory': 'El texto de la memoria',
                'hash': 'hash-string',
                'metadata': {...},
                'created_at': 'timestamp',
                'updated_at': 'timestamp',
                'user_id': 'marcelo'
            },
            ...
        ]
    }
    """
    try:
        crew = initialize_crew()
        
        if not crew.memory_service:
            return "<p style='color: #666; text-align: center; padding: 20px; font-family: Montserrat;'>⚠️ mem0 no está inicializado</p>"
        
        logger.info("🔍 Cargando memorias de mem0...")
        
        # mem0 devuelve un dict con clave 'results'
        response = crew.memory_service.get_all(limit=100)
        
        logger.info(f"📊 Respuesta de mem0: {type(response)}")
        if isinstance(response, dict):
            logger.info(f"📊 Keys: {response.keys()}")
        
        # Extraer la lista de memorias
        if isinstance(response, dict):
            memories = response.get('results', [])
        elif isinstance(response, list):
            memories = response
        else:
            memories = []
        
        logger.info(f"📊 Total memorias encontradas: {len(memories)}")
        
        if not memories:
            return "<p style='color: #666; text-align: center; padding: 20px; font-family: Montserrat;'>📭 No hay memorias almacenadas en mem0</p>"
        
        html = f"""
        <style>
            * {{
                font-family: 'Montserrat', sans-serif !important;
            }}
            .memory-container {{
                max-height: 600px;
                overflow-y: auto;
                padding: 10px;
            }}
            .memory-card {{
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 16px;
                margin: 12px 0;
                background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
                transition: all 0.3s ease;
                box-shadow: 0 2px 4px rgba(0,0,0,0.05);
            }}
            .memory-card:hover {{
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transform: translateY(-2px);
            }}
            .memory-header {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 12px;
                padding-bottom: 8px;
                border-bottom: 2px solid #f0f0f0;
            }}
            .memory-number {{
                font-weight: 700;
                color: #2c3e50;
                font-size: 1.1em;
                font-family: 'Montserrat', sans-serif;
            }}
            .memory-id {{
                font-family: 'Montserrat', monospace;
                font-size: 0.75em;
                color: #95a5a6;
                background: #f8f9fa;
                padding: 4px 8px;
                border-radius: 4px;
            }}
            .memory-text {{
                color: #2c3e50;
                line-height: 1.7;
                margin: 12px 0;
                font-size: 0.95em;
                font-family: 'Montserrat', sans-serif;
                font-weight: 500;
            }}
            .memory-meta {{
                font-size: 0.8em;
                color: #7f8c8d;
                border-top: 1px solid #ecf0f1;
                padding-top: 10px;
                margin-top: 10px;
                font-family: 'Montserrat', sans-serif;
            }}
            .memory-meta-item {{
                display: inline-block;
                margin-right: 15px;
                font-family: 'Montserrat', sans-serif;
            }}
        </style>
        <div class='memory-container'>
        """
        
        for i, mem in enumerate(memories, 1):
            # Parsear correctamente la estructura de mem0
            if isinstance(mem, dict):
                memory_text = mem.get('memory', mem.get('text', 'Sin contenido'))
                memory_id = mem.get('id', f'mem_{i}')
                
                # Parsear fechas
                created = mem.get('created_at', 'Desconocido')
                updated = mem.get('updated_at', 'Desconocido')
                
                # Formatear fechas si existen
                if created != 'Desconocido':
                    try:
                        # Si es timestamp
                        if isinstance(created, (int, float)):
                            created_dt = datetime.fromtimestamp(created)
                            created = created_dt.strftime('%Y-%m-%d %H:%M')
                        # Si es string ISO
                        elif isinstance(created, str):
                            try:
                                created_dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                                created = created_dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass
                    except:
                        pass
                
                if updated != 'Desconocido':
                    try:
                        if isinstance(updated, (int, float)):
                            updated_dt = datetime.fromtimestamp(updated)
                            updated = updated_dt.strftime('%Y-%m-%d %H:%M')
                        elif isinstance(updated, str):
                            try:
                                updated_dt = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                                updated = updated_dt.strftime('%Y-%m-%d %H:%M')
                            except:
                                pass
                    except:
                        pass
                
                # Obtener user_id si existe
                user_id = mem.get('user_id', 'N/A')
                
            elif isinstance(mem, str):
                # Fallback: si es string directo
                memory_text = mem
                memory_id = f"mem_{i}"
                created = "Desconocido"
                updated = "Desconocido"
                user_id = "N/A"
            else:
                # Otro tipo
                memory_text = str(mem)
                memory_id = f"mem_{i}"
                created = "Desconocido"
                updated = "Desconocido"
                user_id = "N/A"
            
            # Truncar ID si es muy largo (para UUIDs)
            display_id = memory_id[:12] + '...' if len(memory_id) > 15 else memory_id
            
            html += f"""
            <div class='memory-card'>
                <div class='memory-header'>
                    <span class='memory-number'>🧠 Memoria #{i}</span>
                    <span class='memory-id' title='{memory_id}'>{display_id}</span>
                </div>
                <div class='memory-text'>{memory_text}</div>
                <div class='memory-meta'>
                    <span class='memory-meta-item'>📅 Creado: {created}</span>
                    <span class='memory-meta-item'>🔄 Actualizado: {updated}</span>
                    <span class='memory-meta-item'>👤 Usuario: {user_id}</span>
                </div>
            </div>
            """
        
        html += "</div>"
        
        return html
        
    except Exception as e:
        logger.error(f"❌ Error cargando memorias: {e}")
        import traceback
        traceback.print_exc()
        return f"<p style='color: red; font-family: Montserrat;'>❌ Error: {str(e)}</p>"


def get_memory_ids_list() -> List[str]:
    """Obtiene lista de IDs de memorias para dropdown."""
    try:
        crew = initialize_crew()
        
        if not crew.memory_service:
            logger.warning("⚠️ memory_service no disponible")
            return []
        
        response = crew.memory_service.get_all(limit=100)
        
        # Extraer lista de memorias
        if isinstance(response, dict):
            memories = response.get('results', [])
        elif isinstance(response, list):
            memories = response
        else:
            memories = []
        
        logger.info(f"📋 Obtenidos {len(memories)} IDs de memorias")
        
        if not memories:
            return []
        
        # Crear opciones legibles: "ID - Preview del texto"
        options = []
        for i, mem in enumerate(memories, 1):
            if isinstance(mem, dict):
                memory_id = mem.get('id', f'mem_{i}')
                text = mem.get('memory', mem.get('text', 'Sin texto'))
            elif isinstance(mem, str):
                memory_id = f"mem_{i}"
                text = mem
            else:
                memory_id = f"mem_{i}"
                text = str(mem)
            
            # Truncar texto para preview
            preview = text[:50] + "..." if len(text) > 50 else text
            option = f"{memory_id}|||{preview}"  # Separador único
            options.append(option)
            
            logger.info(f"  #{i}: {memory_id} - {preview[:30]}...")
        
        return options
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo IDs: {e}")
        import traceback
        traceback.print_exc()
        return []


def delete_memory(memory_option: str) -> Tuple[str, str]:
    """
    Elimina una memoria específica.
    
    FIX v7.3.0: Manejo robusto de IDs con validación.
    """
    try:
        logger.info(f"🗑️ Intentando eliminar: '{memory_option}'")
        
        if not memory_option or memory_option.strip() == "":
            logger.warning("⚠️ Opción vacía")
            return "⚠️ Selecciona una memoria primero", load_all_memories()
        
        crew = initialize_crew()
        
        if not crew.memory_service:
            logger.error("❌ memory_service no disponible")
            return "❌ mem0 no inicializado", load_all_memories()
        
        # Extraer ID usando el separador único
        if "|||" in memory_option:
            memory_id = memory_option.split("|||")[0].strip()
        else:
            # Fallback: usar espacio como separador
            parts = memory_option.split(" - ")
            if len(parts) > 0:
                memory_id = parts[0].strip()
            else:
                memory_id = memory_option.strip()
        
        logger.info(f"🔑 ID extraído: '{memory_id}'")
        
        if not memory_id:
            logger.error("❌ ID vacío después de parseo")
            return "❌ Error: ID inválido", load_all_memories()
        
        # Validar que la memoria existe antes de eliminar
        logger.info(f"🔍 Validando existencia de memoria '{memory_id}'...")
        all_mems = crew.memory_service.get_all(limit=100)
        
        if isinstance(all_mems, dict):
            memories = all_mems.get('results', [])
        elif isinstance(all_mems, list):
            memories = all_mems
        else:
            memories = []
        
        memory_exists = False
        for mem in memories:
            if isinstance(mem, dict):
                if mem.get('id') == memory_id:
                    memory_exists = True
                    logger.info(f"✅ Memoria encontrada: {mem.get('memory', '')[:50]}")
                    break
        
        if not memory_exists:
            logger.warning(f"⚠️ Memoria '{memory_id}' no encontrada en lista")
            return f"⚠️ Memoria '{memory_id}' no encontrada", load_all_memories()
        
        # Intentar eliminar
        logger.info(f"🗑️ Eliminando memoria '{memory_id}'...")
        crew.memory_service.delete(memory_id=memory_id)
        logger.info(f"✅ Memoria '{memory_id}' eliminada")
        
        return f"✅ Memoria eliminada: {memory_id}", load_all_memories()
        
    except Exception as e:
        logger.error(f"❌ Error eliminando memoria: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}", load_all_memories()


def clear_all_memories() -> Tuple[str, str]:
    """Elimina TODAS las memorias."""
    try:
        logger.info("🗑️ Eliminando TODAS las memorias...")
        
        crew = initialize_crew()
        
        if not crew.memory_service:
            logger.error("❌ memory_service no disponible")
            return "❌ mem0 no inicializado", ""
        
        crew.memory_service.delete_all()
        logger.info("✅ Todas las memorias eliminadas")
        
        return "✅ Todas las memorias eliminadas", load_all_memories()
        
    except Exception as e:
        logger.error(f"❌ Error limpiando memorias: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}", load_all_memories()


def create_interface():
    """Crea interfaz Gradio completa con fuente Montserrat."""
    
    # CSS personalizado con Montserrat GLOBAL
    custom_css = """
    /* Importar Montserrat */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    
    /* Aplicar Montserrat a TODO */
    * {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    body {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Mensajes del chat */
    .message {
        font-family: 'Montserrat', sans-serif !important;
        font-size: 15px;
        line-height: 1.7;
    }
    
    /* Contenido en prosa */
    .prose {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Inputs */
    input, textarea, select {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Botones */
    button {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    
    /* Labels */
    label {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 500 !important;
    }
    
    /* Markdown */
    .markdown-text {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Headers en Gradio */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }
    
    /* Tabs */
    .tab-nav button {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    
    /* Dropdowns */
    .dropdown-menu {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    /* Info boxes */
    .gr-box {
        font-family: 'Montserrat', sans-serif !important;
    }
    """
    
    with gr.Blocks(
        title="Minerva Chat", 
        theme=gr.themes.Soft(),
        css=custom_css
    ) as interface:
        
        gr.Markdown("# 🧠 Minerva v7.3.0 - CrewAI + mem0 (CPU)")
        
        with gr.Tabs():
            
            # ============= TAB 1: CHAT =============
            with gr.Tab("💬 Chat"):
                with gr.Row():
                    with gr.Column(scale=4):
                        # FIX: Usar type='messages' en lugar de 'tuples'
                        chatbot = gr.Chatbot(
                            height=400,
                            show_label=False,
                            avatar_images=(None, "🧠"),
                            type="messages"
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
                        
                        gr.Markdown("""
**Modelo:** Phi3 (Ollama)
**Orquestador:** CrewAI 1.1.0
**Memoria:** mem0 1.0.0 (CPU)
**Agentes:** 3

⚠️ **Nota:** CUDA deshabilitado
(GTX 1050 incompatible)
                        """)
                        
                        export_output = gr.Textbox(
                            label="Exportar",
                            lines=10,
                            visible=False
                        )
                
                # Event handlers adaptados a type='messages'
                def user_message(message, history):
                    """Adapta al formato messages de Gradio."""
                    return "", history + [{"role": "user", "content": message}]
                
                def bot_response(history):
                    """Procesa y responde en formato messages."""
                    if not history or history[-1].get("role") != "user":
                        return history, get_loaded_prompts_info()
                    
                    user_msg = history[-1]["content"]
                    
                    # Convertir historial a formato antiguo para chat_function
                    old_format_history = []
                    for msg in history[:-1]:
                        if msg["role"] == "user":
                            old_format_history.append([msg["content"], None])
                        elif msg["role"] == "assistant":
                            if old_format_history and old_format_history[-1][1] is None:
                                old_format_history[-1][1] = msg["content"]
                    
                    bot_msg = chat_function(user_msg, old_format_history)
                    
                    # Agregar respuesta
                    history.append({"role": "assistant", "content": bot_msg})
                    
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
                    lambda: [],
                    None,
                    chatbot,
                    queue=False
                ).then(
                    initialize_conversation,
                    None,
                    None
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
            
            # ============= TAB 2: MEMORIA (mem0) =============
            with gr.Tab("🧠 Memoria (mem0)"):
                
                gr.Markdown("""
                ### Gestión de Memoria (mem0)
                
                mem0 gestiona automáticamente la memoria persistente.
                Extrae, consolida y actualiza información relevante del usuario.
                
                **Características:**
                - ✅ Consolidación automática de información
                - ✅ Actualización inteligente de hechos
                - ✅ Eliminación de duplicados
                - ✅ Memoria que trasciende conversaciones
                
                **Nota:** Ejecutándose en CPU (CUDA deshabilitado para GTX 1050)
                """)
                
                with gr.Row():
                    refresh_mem_btn = gr.Button("🔄 Recargar Memorias", variant="primary", scale=1)
                    clear_all_mem_btn = gr.Button("🗑️ Eliminar TODAS", variant="stop", scale=1)
                
                memory_result = gr.Markdown("")
                
                memories_display = gr.HTML(
                    value=load_all_memories(),
                    label="Memorias"
                )
                
                gr.Markdown("---")
                gr.Markdown("### Eliminar Memoria Individual")
                
                with gr.Row():
                    memory_selector = gr.Dropdown(
                        choices=[],
                        label="Selecciona una memoria para eliminar",
                        scale=3,
                        allow_custom_value=True
                    )
                    delete_memory_btn = gr.Button("🗑️ Eliminar", variant="stop", scale=1)
                
                delete_result = gr.Markdown("")
                
                # Eventos
                def refresh_memories_and_dropdown():
                    memories_html = load_all_memories()
                    memory_options = get_memory_ids_list()
                    return memories_html, gr.Dropdown(choices=memory_options)
                
                refresh_mem_btn.click(
                    refresh_memories_and_dropdown,
                    None,
                    [memories_display, memory_selector]
                )
                
                delete_memory_btn.click(
                    delete_memory,
                    inputs=memory_selector,
                    outputs=[delete_result, memories_display]
                ).then(
                    refresh_memories_and_dropdown,
                    None,
                    [memories_display, memory_selector]
                )
                
                clear_all_mem_btn.click(
                    clear_all_memories,
                    None,
                    [memory_result, memories_display]
                ).then(
                    refresh_memories_and_dropdown,
                    None,
                    [memories_display, memory_selector]
                )
                
                # Cargar dropdown inicial
                interface.load(
                    get_memory_ids_list,
                    None,
                    memory_selector
                )
        
        gr.Markdown(
            """
            ---
            <div style='text-align: center; color: #666; font-size: 0.9em; font-family: Montserrat;'>
                🧠 <strong>Minerva v7.3.0</strong> - CrewAI + mem0 (CPU) + Debugging Mejorado
            </div>
            """
        )
    
    return interface


if __name__ == "__main__":
    demo = create_interface()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )