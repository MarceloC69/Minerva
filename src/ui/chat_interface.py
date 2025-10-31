# src/ui/chat_interface.py - v8.0.0 FIXED - Memoria + Documentos
"""
Interfaz de chat de Minerva con memoria persistente (mem0) + Gestión de Documentos.

FIXES v8.0.0:
- ✅ Memoria mem0 corregida con mejor prompt de extracción
- ✅ Tab de Documentos restaurado (subir, indexar, ver, eliminar)
- ✅ Mejor control de lo que se guarda en memoria
- ✅ Validación de calidad de memorias
- ✅ Todas las funcionalidades originales preservadas
"""

import gradio as gr
import logging
import os
from datetime import datetime
from typing import Tuple, List
from pathlib import Path

# 🔧 FIX CUDA: Forzar CPU para mem0 (evitar error con GTX 1050)
os.environ['CUDA_VISIBLE_DEVICES'] = ''
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
    """Inicializa MinervaCrew con CrewAI + mem0 mejorado."""
    global crew
    
    if crew is None:
        logger.info("🚀 Inicializando MinervaCrew (CrewAI + mem0 mejorado)...")
        
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
        
        # Inicializar mem0 (en CPU) - MEJORADO
        try:
            logger.info("🧠 Inicializando mem0 mejorado en CPU...")
            memory_service = Mem0Wrapper(user_id="marcelo", organization_id="minerva")
            logger.info("✅ mem0 inicializado correctamente")
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
        
        # Procesar con MinervaCrew
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
            'source_retrieval': '🔗',
            'personal': '👤'
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
        
        from src.memory.langchain_memory import LangChainMemoryWrapper
        from config.settings import settings
        
        memory = LangChainMemoryWrapper(
            db_path=str(settings.SQLITE_PATH),
            conversation_id=current_conversation_id
        )
        
        messages = memory.get_messages()
        
        if not messages:
            return "Conversación vacía."
        
        export_text = f"=== Conversación Minerva ===\n"
        export_text += f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        export_text += f"ID: {current_conversation_id}\n"
        export_text += "=" * 50 + "\n\n"
        
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
    """Carga todas las memorias de mem0."""
    try:
        crew = initialize_crew()
        
        if not crew.memory_service:
            return "<p style='color: #666; text-align: center; padding: 20px; font-family: Montserrat;'>⚠️ mem0 no está inicializado</p>"
        
        logger.info("🔍 Cargando memorias de mem0...")
        
        response = crew.memory_service.get_all(limit=100)
        
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
            if isinstance(mem, dict):
                memory_text = mem.get('memory', mem.get('text', 'Sin contenido'))
                memory_id = mem.get('id', f'mem_{i}')
                
                created = mem.get('created_at', 'Desconocido')
                updated = mem.get('updated_at', 'Desconocido')
                
                if created != 'Desconocido':
                    try:
                        if isinstance(created, (int, float)):
                            created_dt = datetime.fromtimestamp(created)
                            created = created_dt.strftime('%Y-%m-%d %H:%M')
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
                
                user_id = mem.get('user_id', 'N/A')
                
            elif isinstance(mem, str):
                memory_text = mem
                memory_id = f"mem_{i}"
                created = "Desconocido"
                updated = "Desconocido"
                user_id = "N/A"
            else:
                memory_text = str(mem)
                memory_id = f"mem_{i}"
                created = "Desconocido"
                updated = "Desconocido"
                user_id = "N/A"
            
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
        
        if isinstance(response, dict):
            memories = response.get('results', [])
        elif isinstance(response, list):
            memories = response
        else:
            memories = []
        
        logger.info(f"📋 Obtenidos {len(memories)} IDs de memorias")
        
        if not memories:
            return []
        
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
            
            preview = text[:50] + "..." if len(text) > 50 else text
            option = f"{memory_id}|||{preview}"
            options.append(option)
            
            logger.info(f"  #{i}: {memory_id} - {preview[:30]}...")
        
        return options
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo IDs: {e}")
        import traceback
        traceback.print_exc()
        return []


def delete_memory(memory_option: str) -> Tuple[str, str]:
    """Elimina una memoria específica."""
    try:
        logger.info(f"🗑️ Intentando eliminar: '{memory_option}'")
        
        if not memory_option or memory_option.strip() == "":
            logger.warning("⚠️ Opción vacía")
            return "⚠️ Selecciona una memoria primero", load_all_memories()
        
        crew = initialize_crew()
        
        if not crew.memory_service:
            logger.error("❌ memory_service no disponible")
            return "❌ mem0 no inicializado", load_all_memories()
        
        if "|||" in memory_option:
            memory_id = memory_option.split("|||")[0].strip()
        else:
            parts = memory_option.split(" - ")
            if len(parts) > 0:
                memory_id = parts[0].strip()
            else:
                memory_id = memory_option.strip()
        
        logger.info(f"🔑 ID extraído: '{memory_id}'")
        
        if not memory_id:
            logger.error("❌ ID vacío después de parseo")
            return "❌ Error: ID inválido", load_all_memories()
        
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


# ==================== GESTIÓN DE DOCUMENTOS ====================

def load_documents_list() -> str:
    """Carga la lista de documentos indexados en formato HTML."""
    try:
        crew = initialize_crew()
        
        documents = crew.db_manager.get_documents(limit=50)
        
        if not documents:
            return "<p style='color: #666; text-align: center; padding: 20px;'>📭 No hay documentos indexados</p>"
        
        html = """
        <style>
            .doc-table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            .doc-table th {
                background: #f0f0f0;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #ddd;
            }
            .doc-table td {
                padding: 10px 12px;
                border-bottom: 1px solid #eee;
            }
            .doc-table tr:hover {
                background: #f9f9f9;
            }
            .badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: 500;
            }
            .badge-pdf {
                background: #fee;
                color: #c00;
            }
            .badge-docx {
                background: #eef;
                color: #00c;
            }
            .badge-txt {
                background: #efe;
                color: #0c0;
            }
        </style>
        <table class='doc-table'>
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Nombre</th>
                    <th>Tipo</th>
                    <th>Chunks</th>
                    <th>Indexado</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for doc in documents:
            badge_class = f"badge-{doc.file_type.lower()}"
            
            html += f"""
                <tr>
                    <td><strong>#{doc.id}</strong></td>
                    <td>{doc.filename}</td>
                    <td><span class='badge {badge_class}'>{doc.file_type.upper()}</span></td>
                    <td>{doc.chunk_count or 'N/A'}</td>
                    <td>{doc.processed_at.strftime('%Y-%m-%d %H:%M')}</td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Error cargando documentos: {e}")
        return f"<p style='color: red;'>❌ Error: {str(e)}</p>"


def upload_and_index_document(file) -> Tuple[str, str]:
    """
    Procesa y indexa un documento subido.
    
    Args:
        file: Archivo subido por Gradio
        
    Returns:
        Tupla de (mensaje_resultado, lista_documentos_actualizada)
    """
    try:
        if file is None:
            return "⚠️ No se seleccionó ningún archivo", load_documents_list()
        
        crew = initialize_crew()
        
        file_path = Path(file.name)
        
        logger.info(f"📄 Procesando archivo: {file_path.name}")
        
        result = crew.indexer.index_document(
            file_path=file_path,
            collection_name="knowledge_base"
        )
        
        if result.get('success'):
            msg = f"""
            ✅ **Documento indexado exitosamente**
            
            📄 **Archivo:** {result['filename']}
            📊 **Chunks creados:** {result['chunks_created']}
            ⏱️ **Tiempo:** {result['processing_time_seconds']:.2f}s
            🆔 **ID en DB:** {result['document_id']}
            
            💡 Ahora puedes hacer preguntas sobre este documento.
            """
        else:
            msg = f"❌ Error indexando documento: {result.get('error', 'Unknown error')}"
        
        return msg, load_documents_list()
        
    except Exception as e:
        logger.error(f"❌ Error en upload_and_index: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error: {str(e)}", load_documents_list()


def delete_document_by_id(document_id: int) -> Tuple[str, str]:
    """
    Elimina un documento del índice.
    
    Args:
        document_id: ID del documento a eliminar
        
    Returns:
        Tupla de (mensaje_resultado, lista_documentos_actualizada)
    """
    try:
        if not document_id or document_id <= 0:
            return "⚠️ Debes ingresar un ID válido", load_documents_list()
        
        crew = initialize_crew()
        
        success = crew.indexer.delete_document(
            document_id=int(document_id),
            collection_name="knowledge_base"
        )
        
        if success:
            msg = f"✅ Documento #{document_id} eliminado del índice"
        else:
            msg = f"❌ Error eliminando documento #{document_id}"
        
        return msg, load_documents_list()
        
    except Exception as e:
        logger.error(f"❌ Error eliminando documento: {e}")
        return f"❌ Error: {str(e)}", load_documents_list()


def get_document_ids_list() -> List[int]:
    """Obtiene lista de IDs de documentos para dropdown."""
    try:
        crew = initialize_crew()
        
        documents = crew.db_manager.get_documents(limit=100)
        
        if not documents:
            return []
        
        return [doc.id for doc in documents]
        
    except Exception as e:
        logger.error(f"Error obteniendo IDs de documentos: {e}")
        return []


def create_interface():
    """Crea interfaz Gradio completa con fuente Montserrat."""
    
    custom_css = """
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');
    
    * {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    body {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    .message {
        font-family: 'Montserrat', sans-serif !important;
        font-size: 15px;
        line-height: 1.7;
    }
    
    .prose {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    input, textarea, select {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    button {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    
    label {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 500 !important;
    }
    
    .markdown-text {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 700 !important;
    }
    
    .tab-nav button {
        font-family: 'Montserrat', sans-serif !important;
        font-weight: 600 !important;
    }
    
    .dropdown-menu {
        font-family: 'Montserrat', sans-serif !important;
    }
    
    .gr-box {
        font-family: 'Montserrat', sans-serif !important;
    }
    """
    
    with gr.Blocks(
        title="Minerva Chat", 
        theme=gr.themes.Soft(),
        css=custom_css
    ) as interface:
        
        gr.Markdown("# 🧠 Minerva v8.0.0 - CrewAI + mem0 Mejorado + Documentos")
        
        with gr.Tabs():
            
            # ============= TAB 1: CHAT =============
            with gr.Tab("💬 Chat"):
                with gr.Row():
                    with gr.Column(scale=4):
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

✅ **Memoria mejorada**
✅ **Documentos restaurados**
                        """)
                        
                        export_output = gr.Textbox(
                            label="Exportar",
                            lines=10,
                            visible=False
                        )
                
                def user_message(message, history):
                    return "", history + [{"role": "user", "content": message}]
                
                def bot_response(history):
                    if not history or history[-1].get("role") != "user":
                        return history, get_loaded_prompts_info()
                    
                    user_msg = history[-1]["content"]
                    
                    old_format_history = []
                    for msg in history[:-1]:
                        if msg["role"] == "user":
                            old_format_history.append([msg["content"], None])
                        elif msg["role"] == "assistant":
                            if old_format_history and old_format_history[-1][1] is None:
                                old_format_history[-1][1] = msg["content"]
                    
                    bot_msg = chat_function(user_msg, old_format_history)
                    
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
            
            # ============= TAB 2: DOCUMENTOS =============
            with gr.Tab("📚 Documentos"):
                
                gr.Markdown("""
                ### Gestión de Documentos (RAG)
                
                Sube documentos para que Minerva pueda responder preguntas sobre ellos.
                
                **Formatos soportados:**
                - 📕 PDF (.pdf)
                - 📘 Word (.docx)
                - 📄 Texto (.txt)
                - 📝 Markdown (.md)
                """)
                
                with gr.Row():
                    with gr.Column(scale=2):
                        gr.Markdown("#### 📤 Subir Documento")
                        
                        file_upload = gr.File(
                            label="Selecciona un archivo",
                            file_types=[".pdf", ".docx", ".txt", ".md"]
                        )
                        
                        upload_btn = gr.Button("📤 Subir e Indexar", variant="primary")
                        
                        upload_result = gr.Markdown("")
                    
                    with gr.Column(scale=2):
                        gr.Markdown("#### 🗑️ Eliminar Documento")
                        
                        doc_id_input = gr.Number(
                            label="ID del documento",
                            value=1,
                            precision=0,
                            minimum=1
                        )
                        
                        delete_doc_btn = gr.Button("🗑️ Eliminar", variant="stop")
                        
                        delete_result = gr.Markdown("")
                
                gr.Markdown("---")
                gr.Markdown("#### 📋 Documentos Indexados")
                
                refresh_docs_btn = gr.Button("🔄 Recargar Lista")
                
                documents_display = gr.HTML(
                    value=load_documents_list(),
                    label="Documentos"
                )
                
                upload_btn.click(
                    upload_and_index_document,
                    inputs=file_upload,
                    outputs=[upload_result, documents_display]
                )
                
                delete_doc_btn.click(
                    delete_document_by_id,
                    inputs=doc_id_input,
                    outputs=[delete_result, documents_display]
                )
                
                refresh_docs_btn.click(
                    load_documents_list,
                    None,
                    documents_display
                )
            
            # ============= TAB 3: MEMORIA (mem0) =============
            with gr.Tab("🧠 Memoria (mem0)"):
                
                gr.Markdown("""
                ### Gestión de Memoria (mem0)
                
                mem0 gestiona automáticamente la memoria persistente.
                
                **Características mejoradas v8.0:**
                - ✅ Extracción más inteligente de información
                - ✅ Validación de calidad de memorias
                - ✅ Mejor consolidación de datos
                - ✅ Menos "alucinaciones"
                
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
                
                interface.load(
                    get_memory_ids_list,
                    None,
                    memory_selector
                )
        
        gr.Markdown(
            """
            ---
            <div style='text-align: center; color: #666; font-size: 0.9em; font-family: Montserrat;'>
                🧠 <strong>Minerva v8.0.0</strong> - CrewAI + mem0 Mejorado + Gestión de Documentos Restaurada
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