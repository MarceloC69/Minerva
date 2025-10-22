# src/ui/prompt_admin.py - v2.0.0 - Con creación de prompts
"""
Interfaz de Gradio para gestionar prompts versionados.
Permite crear, editar, activar y ver historial de prompts.
TODOS LOS DATOS SE LEEN DINÁMICAMENTE DE LA BASE DE DATOS.
"""

import gradio as gr
from pathlib import Path
from typing import List, Tuple, Optional
import logging
from datetime import datetime

from src.database.prompt_manager import PromptManager
from src.database.manager import DatabaseManager
from config.settings import settings

logger = logging.getLogger(__name__)

# Manager global
prompt_manager = None


def initialize_prompt_manager():
    """Inicializa el PromptManager de forma lazy."""
    global prompt_manager
    if prompt_manager is None:
        logger.info("Inicializando PromptManager...")
        db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
        prompt_manager = PromptManager(db_manager=db_manager)
        logger.info("✅ PromptManager inicializado")
    return prompt_manager


def get_agent_types() -> List[str]:
    """
    Retorna los tipos de agentes disponibles DESDE LA BASE DE DATOS.
    No hay valores hardcodeados.
    """
    try:
        import sqlite3
        conn = sqlite3.connect(str(settings.SQLITE_PATH))
        cursor = conn.execute("""
            SELECT DISTINCT agent_type 
            FROM prompt_versions 
            ORDER BY agent_type
        """)
        
        agent_types = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not agent_types:
            logger.warning("⚠️ No hay agent_types en la base de datos")
            return ["(no hay agentes)"]
        
        logger.info(f"✅ Agent types cargados desde DB: {agent_types}")
        return agent_types
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo agent_types: {e}")
        return ["Error cargando agentes"]


def get_prompt_names_for_agent(agent_type: str):
    """
    Obtiene los nombres de prompts que existen para un agente específico.
    
    Args:
        agent_type: Tipo de agente
        
    Returns:
        gr.Dropdown.update con las opciones actualizadas
    """
    if not agent_type or agent_type == "Selecciona...":
        return gr.Dropdown(
            choices=["Selecciona primero un agente..."],
            value="Selecciona primero un agente...",
            interactive=False
        )
    
    try:
        import sqlite3
        conn = sqlite3.connect(str(settings.SQLITE_PATH))
        cursor = conn.execute("""
            SELECT DISTINCT prompt_name 
            FROM prompt_versions 
            WHERE agent_type = ?
            ORDER BY prompt_name
        """, (agent_type,))
        
        names = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        if not names:
            return gr.Dropdown(
                choices=["(no hay prompts para este agente)"],
                value="(no hay prompts para este agente)",
                interactive=False
            )
        
        return gr.Dropdown(
            choices=names,
            value=names[0],
            interactive=True
        )
        
    except Exception as e:
        logger.error(f"Error obteniendo nombres de prompts: {e}")
        return gr.Dropdown(
            choices=["Error cargando prompts"],
            value="Error cargando prompts",
            interactive=False
        )


def get_all_agent_types_for_filter() -> List[str]:
    """Retorna tipos de agentes con la opción 'Todos' para filtros."""
    agent_types = get_agent_types()
    if agent_types and agent_types[0] != "(no hay agentes)":
        return ["Todos"] + agent_types
    return ["Todos"]


def load_prompts_list(agent_filter: str = "Todos") -> str:
    """
    Carga la lista de prompts en formato tabla HTML.
    
    Args:
        agent_filter: Filtro por tipo de agente
        
    Returns:
        HTML con la tabla de prompts
    """
    try:
        pm = initialize_prompt_manager()
        
        if agent_filter == "Todos":
            all_prompts = pm.get_all_active_prompts()
        else:
            all_prompts = pm.get_all_active_prompts(agent_type=agent_filter.lower())
        
        if not all_prompts:
            return "<p style='color: #666; text-align: center; padding: 20px;'>📭 No hay prompts activos</p>"
        
        html = """
        <style>
            .prompt-table {
                width: 100%;
                border-collapse: collapse;
                margin: 10px 0;
            }
            .prompt-table th {
                background: #f0f0f0;
                padding: 12px;
                text-align: left;
                font-weight: 600;
                border-bottom: 2px solid #ddd;
            }
            .prompt-table td {
                padding: 10px 12px;
                border-bottom: 1px solid #eee;
            }
            .prompt-table tr:hover {
                background: #f9f9f9;
            }
            .badge {
                display: inline-block;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.85em;
                font-weight: 500;
            }
            .badge-active {
                background: #d4edda;
                color: #155724;
            }
            .prompt-preview {
                max-width: 300px;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
                font-family: monospace;
                font-size: 0.9em;
                color: #555;
            }
        </style>
        <table class='prompt-table'>
            <thead>
                <tr>
                    <th>Agente</th>
                    <th>Nombre</th>
                    <th>Estado</th>
                    <th>Preview</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for key, content in all_prompts.items():
            agent_type, prompt_name = key.split('.', 1)
            preview = content[:100] + "..." if len(content) > 100 else content
            
            html += f"""
                <tr>
                    <td><strong>{agent_type}</strong></td>
                    <td>{prompt_name}</td>
                    <td><span class='badge badge-active'>✅ Activo</span></td>
                    <td><div class='prompt-preview'>{preview}</div></td>
                </tr>
            """
        
        html += """
            </tbody>
        </table>
        """
        
        return html
        
    except Exception as e:
        logger.error(f"Error cargando prompts: {e}")
        return f"<p style='color: red;'>❌ Error: {str(e)}</p>"


def load_prompt_for_edit(agent_type: str, prompt_name: str) -> Tuple[str, str, str]:
    """
    Carga un prompt para editar.
    
    Returns:
        Tupla de (contenido, info_versión, historial_html)
    """
    try:
        pm = initialize_prompt_manager()
        
        content = pm.get_active_prompt(agent_type, prompt_name)
        
        if not content:
            return (
                "",
                f"⚠️ No hay versión activa para {agent_type}.{prompt_name}",
                ""
            )
        
        history = pm.get_prompt_history(agent_type, prompt_name, limit=5)
        
        active = next((v for v in history if v.is_active), None)
        if active:
            info = f"""
            **Versión activa**: v{active.version}  
            **Creada**: {active.created_at.strftime('%Y-%m-%d %H:%M')}  
            **Por**: {active.created_by}  
            **Usos**: {active.usage_count}
            """
        else:
            info = "ℹ️ Sin información de versión"
        
        hist_html = "<div style='margin-top: 10px;'><strong>📜 Historial de Versiones:</strong><ul>"
        for v in history[:5]:
            status = "✅ ACTIVA" if v.is_active else "⚪"
            hist_html += f"""
            <li>
                <strong>v{v.version}</strong> {status} - 
                {v.created_at.strftime('%Y-%m-%d %H:%M')} - 
                {v.description or 'Sin descripción'}
            </li>
            """
        hist_html += "</ul></div>"
        
        return content, info, hist_html
        
    except Exception as e:
        logger.error(f"Error cargando prompt: {e}")
        return "", f"❌ Error: {str(e)}", ""


def save_new_version(
    agent_type: str,
    prompt_name: str,
    content: str,
    description: str,
    auto_activate: bool,
    created_by: str
) -> Tuple[str, str, str, str, str]:
    """
    Guarda una nueva versión del prompt.
    
    Returns:
        Tupla de (mensaje_resultado, prompts_list_html, nuevo_contenido, nueva_info, nuevo_historial)
    """
    try:
        if not agent_type or agent_type == "Selecciona...":
            return "⚠️ Debes seleccionar un tipo de agente", load_prompts_list(), content, "", ""
        
        if not prompt_name or prompt_name == "Selecciona primero un agente...":
            return "⚠️ Debes seleccionar un nombre de prompt", load_prompts_list(), content, "", ""
        
        if not content or len(content.strip()) < 10:
            return "⚠️ El contenido del prompt debe tener al menos 10 caracteres", load_prompts_list(), content, "", ""
        
        pm = initialize_prompt_manager()
        
        new_version = pm.create_prompt_version(
            agent_type=agent_type,
            prompt_name=prompt_name,
            content=content.strip(),
            description=description or f"Actualización desde UI - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_by=created_by or "admin",
            auto_activate=auto_activate
        )
        
        result_msg = f"""
        ✅ **Nueva versión creada exitosamente**
        
        - Agente: {agent_type}
        - Prompt: {prompt_name}
        - Versión: v{new_version.version}
        - Estado: {'✅ Activada' if new_version.is_active else '⚪ Inactiva'}
        
        💡 **Tip:** El cambio es inmediato. El siguiente mensaje en el chat usará el nuevo prompt.
        """
        
        updated_list = load_prompts_list()
        new_content, new_info, new_hist = load_prompt_for_edit(agent_type, prompt_name)
        
        return result_msg, updated_list, new_content, new_info, new_hist
        
    except Exception as e:
        logger.error(f"Error guardando prompt: {e}")
        return f"❌ Error al guardar: {str(e)}", load_prompts_list(), content, "", ""


def create_new_prompt(
    new_agent_type: str,
    new_prompt_name: str,
    new_content: str,
    new_description: str,
    new_created_by: str,
    auto_activate: bool
) -> Tuple[str, str]:
    """
    Crea un prompt completamente nuevo.
    
    Returns:
        Tupla de (mensaje_resultado, prompts_list_actualizada)
    """
    try:
        if not new_agent_type or len(new_agent_type.strip()) < 2:
            return "⚠️ El tipo de agente debe tener al menos 2 caracteres", load_prompts_list()
        
        if not new_prompt_name or len(new_prompt_name.strip()) < 2:
            return "⚠️ El nombre del prompt debe tener al menos 2 caracteres", load_prompts_list()
        
        if not new_content or len(new_content.strip()) < 10:
            return "⚠️ El contenido debe tener al menos 10 caracteres", load_prompts_list()
        
        new_agent_type = new_agent_type.strip().lower()
        new_prompt_name = new_prompt_name.strip().lower().replace(' ', '_')
        
        pm = initialize_prompt_manager()
        
        # Verificar si ya existe
        existing = pm.get_active_prompt(new_agent_type, new_prompt_name)
        if existing:
            return f"⚠️ Ya existe un prompt '{new_prompt_name}' para el agente '{new_agent_type}'.\n\nUsa el tab 'Editar' para modificarlo.", load_prompts_list()
        
        # USAR create_prompt_version en lugar de create_prompt
        new_prompt = pm.create_prompt_version(
            agent_type=new_agent_type,
            prompt_name=new_prompt_name,
            content=new_content.strip(),
            description=new_description or f"Prompt creado desde UI - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            created_by=new_created_by or "admin",
            auto_activate=auto_activate
        )
        
        result_msg = f"""
        ✅ **Prompt creado exitosamente**
        
        - **Agente:** `{new_agent_type}`
        - **Nombre:** `{new_prompt_name}`
        - **Versión:** v{new_prompt.version}
        - **Estado:** {'✅ Activo' if new_prompt.is_active else '⚪ Inactivo'}
        
        💡 **Próximos pasos:**
        1. El prompt ya está disponible para usar
        2. Puedes editarlo en el tab "Editar Prompt"
        3. El agente lo cargará automáticamente en la próxima interacción
        
        🎯 **Para usarlo en código:**
```python
        prompt = prompt_manager.get_active_prompt('{new_agent_type}', '{new_prompt_name}')
```
        """
        
        updated_list = load_prompts_list()
        
        return result_msg, updated_list
        
    except Exception as e:
        logger.error(f"Error creando prompt: {e}")
        import traceback
        traceback.print_exc()
        return f"❌ Error al crear prompt: {str(e)}", load_prompts_list()

def clear_create_form() -> Tuple[str, str, str, str, str]:
    """Limpia el formulario de creación."""
    return "", "", "", "", "admin"


def get_version_history(agent_type: str, prompt_name: str) -> str:
    """Obtiene el historial completo de versiones en formato HTML."""
    try:
        if not agent_type or not prompt_name or agent_type == "Selecciona..." or prompt_name == "Selecciona primero un agente...":
            return "<p style='color: #666;'>Selecciona un agente y prompt para ver el historial</p>"
        
        pm = initialize_prompt_manager()
        history = pm.get_prompt_history(agent_type, prompt_name, limit=20)
        
        if not history:
            return f"<p style='color: #666;'>📭 No hay historial para {agent_type}.{prompt_name}</p>"
        
        html = """
        <style>
            .version-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 12px;
                margin: 8px 0;
                background: white;
            }
            .version-card.active {
                border-color: #28a745;
                background: #f0fff0;
            }
            .version-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 8px;
            }
            .version-title {
                font-weight: 600;
                font-size: 1.1em;
            }
            .version-meta {
                font-size: 0.9em;
                color: #666;
            }
            .version-content {
                font-family: monospace;
                background: #f5f5f5;
                padding: 10px;
                border-radius: 4px;
                font-size: 0.85em;
                max-height: 300px;
                overflow-y: auto;
                white-space: pre-wrap;
                word-wrap: break-word;
                line-height: 1.4;
            }
        </style>
        """
        
        for v in history:
            active_class = "active" if v.is_active else ""
            status_badge = "✅ ACTIVA" if v.is_active else "⚪ Inactiva"
            
            content_display = v.content
            
            html += f"""
            <div class='version-card {active_class}'>
                <div class='version-header'>
                    <span class='version-title'>Versión {v.version} - {status_badge}</span>
                    <span class='version-meta'>Usos: {v.usage_count}</span>
                </div>
                <div class='version-meta'>
                    📅 {v.created_at.strftime('%Y-%m-%d %H:%M')} | 
                    👤 {v.created_by} | 
                    📝 {v.description or 'Sin descripción'}
                </div>
                <div class='version-content'>{content_display}</div>
            </div>
            """
        
        return html
        
    except Exception as e:
        logger.error(f"Error obteniendo historial: {e}")
        return f"<p style='color: red;'>❌ Error: {str(e)}</p>"


def export_all_prompts() -> Tuple[str, str]:
    """
    Exporta todos los prompts activos a un archivo de texto descargable.
    
    Returns:
        Tupla de (ruta_archivo, mensaje_resultado)
    """
    try:
        pm = initialize_prompt_manager()
        
        all_prompts = pm.get_all_active_prompts()
        
        if not all_prompts:
            return None, "⚠️ No hay prompts activos para exportar"
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"minerva_prompts_export_{timestamp}.txt"
        
        temp_dir = Path("data/exports")
        temp_dir.mkdir(parents=True, exist_ok=True)
        filepath = temp_dir / filename
        
        lines = [
            "=" * 80,
            "MINERVA - EXPORTACIÓN DE PROMPTS",
            f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total de prompts: {len(all_prompts)}",
            "=" * 80,
            ""
        ]
        
        by_agent = {}
        for key, content in all_prompts.items():
            agent_type, prompt_name = key.split('.', 1)
            if agent_type not in by_agent:
                by_agent[agent_type] = {}
            by_agent[agent_type][prompt_name] = content
        
        for agent_type in sorted(by_agent.keys()):
            lines.append("")
            lines.append("#" * 80)
            lines.append(f"# AGENTE: {agent_type.upper()}")
            lines.append("#" * 80)
            lines.append("")
            
            for prompt_name in sorted(by_agent[agent_type].keys()):
                content = by_agent[agent_type][prompt_name]
                
                lines.append("-" * 80)
                lines.append(f"Prompt: {prompt_name}")
                lines.append("-" * 80)
                lines.append(content)
                lines.append("")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        result_msg = f"""
        ✅ **Exportación completada exitosamente**
        
        📄 **Archivo:** `{filename}`
        📊 **Prompts exportados:** {len(all_prompts)}
        
        👇 **Haz clic en el botón de descarga abajo para guardar el archivo en tu computadora**
        """
        
        logger.info(f"Prompts exportados a: {filepath}")
        
        return str(filepath), result_msg
        
    except Exception as e:
        logger.error(f"Error exportando prompts: {e}")
        return None, f"❌ Error al exportar: {str(e)}"


def export_and_preview(filepath, msg):
    """Genera preview del archivo exportado."""
    if not filepath:
        return filepath, msg, ""
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        preview = content[:5000]
        if len(content) > 5000:
            preview += "\n\n... (archivo completo disponible en la descarga)"
        
        return filepath, msg, preview
    except Exception as e:
        return filepath, msg, f"Error leyendo archivo: {e}"


def activate_version_by_id(agent_type: str, prompt_name: str, version_number: int) -> Tuple[str, str]:
    """
    Activa una versión específica por su número.
    
    Returns:
        Tupla de (mensaje, historial_actualizado)
    """
    try:
        if not agent_type or not prompt_name:
            return "⚠️ Debes seleccionar agente y prompt", ""
        
        pm = initialize_prompt_manager()
        
        history = pm.get_prompt_history(agent_type, prompt_name, limit=50)
        target = next((v for v in history if v.version == version_number), None)
        
        if not target:
            return f"❌ No se encontró la versión {version_number}", get_version_history(agent_type, prompt_name)
        
        success = pm.activate_prompt_version(target.id)
        
        if success:
            msg = f"""
            ✅ **Versión {version_number} activada exitosamente**
            
            💡 **Tip:** El cambio es inmediato. El siguiente mensaje en el chat usará esta versión del prompt.
            """
        else:
            msg = f"❌ Error activando versión {version_number}"
        
        return msg, get_version_history(agent_type, prompt_name)
        
    except Exception as e:
        logger.error(f"Error activando versión: {e}")
        return f"❌ Error: {str(e)}", get_version_history(agent_type, prompt_name)


def clear_edit_form() -> Tuple[str, str, str, str, str]:
    """Limpia el formulario de edición."""
    return (
        "Selecciona...",
        "Selecciona primero un agente...",
        "",
        "",
        ""
    )


def create_prompt_admin_interface() -> gr.Blocks:
    """
    Crea la interfaz de administración de prompts.
    
    Returns:
        Bloque de Gradio configurado
    """
    
    with gr.Blocks() as admin_interface:
        
        gr.Markdown("## 📝 Administración de Prompts")
        gr.Markdown("Gestiona los prompts de todos los agentes de Minerva. **Todos los datos se leen dinámicamente de la base de datos.**")
        
        with gr.Tabs():
            
            # ============= TAB 1: VER PROMPTS =============
            with gr.Tab("📋 Prompts Activos"):
                
                with gr.Row():
                    agent_filter = gr.Dropdown(
                        choices=get_all_agent_types_for_filter(),
                        value="Todos",
                        label="Filtrar por Agente",
                        scale=2
                    )
                    refresh_btn = gr.Button("🔄 Recargar", scale=1)
                
                prompts_display = gr.HTML(
                    value=load_prompts_list(),
                    label="Lista de Prompts"
                )
                
                agent_filter.change(
                    fn=load_prompts_list,
                    inputs=agent_filter,
                    outputs=prompts_display
                )
                
                refresh_btn.click(
                    fn=load_prompts_list,
                    inputs=agent_filter,
                    outputs=prompts_display
                )
            
            # ============= TAB 2: CREAR NUEVO =============
            with gr.Tab("➕ Crear Nuevo Prompt"):
                
                gr.Markdown("""
                ### Crear un Prompt Nuevo
                
                Usa este formulario para crear prompts para:
                - 🤖 Nuevos agentes que estés desarrollando
                - 📝 Nuevas funcionalidades de agentes existentes
                - 🧪 Experimentos con diferentes enfoques de prompting
                
                💡 **Tip:** Los nombres se formatean automáticamente (minúsculas, guiones bajos)
                """)
                
                with gr.Row():
                    new_agent_type_input = gr.Textbox(
                        label="Tipo de Agente",
                        placeholder="Ej: router, conversational, memory_analyzer",
                        scale=1
                    )
                    new_prompt_name_input = gr.Textbox(
                        label="Nombre del Prompt",
                        placeholder="Ej: classification_prompt, system_prompt",
                        scale=1
                    )
                
                gr.Markdown("### Contenido del Prompt")
                
                new_content_input = gr.Textbox(
                    label="Contenido",
                    placeholder="Escribe aquí el contenido completo del prompt...\n\nPuedes usar {placeholders} que se reemplazarán en runtime.",
                    lines=15,
                    max_lines=30
                )
                
                gr.Markdown("### Metadatos")
                
                with gr.Row():
                    new_description_input = gr.Textbox(
                        label="Descripción",
                        placeholder="Ej: Prompt para clasificar intención del usuario usando LLM",
                        lines=2,
                        scale=3
                    )
                    new_created_by_input = gr.Textbox(
                        label="Creado por",
                        value="admin",
                        scale=1
                    )
                
                new_auto_activate_check = gr.Checkbox(
                    label="✅ Activar automáticamente (recomendado para prompts nuevos)",
                    value=True
                )
                
                with gr.Row():
                    create_prompt_btn = gr.Button(
                        "➕ Crear Prompt",
                        variant="primary",
                        size="lg",
                        scale=3
                    )
                    clear_create_btn = gr.Button(
                        "🗑️ Limpiar Formulario",
                        size="lg",
                        scale=1
                    )
                
                create_result = gr.Markdown("")
                
                create_prompt_btn.click(
                    fn=create_new_prompt,
                    inputs=[
                        new_agent_type_input,
                        new_prompt_name_input,
                        new_content_input,
                        new_description_input,
                        new_created_by_input,
                        new_auto_activate_check
                    ],
                    outputs=[create_result, prompts_display]
                )
                
                clear_create_btn.click(
                    fn=clear_create_form,
                    inputs=None,
                    outputs=[
                        new_agent_type_input,
                        new_prompt_name_input,
                        new_content_input,
                        new_description_input,
                        new_created_by_input
                    ]
                )
            
            # ============= TAB 3: EDITAR =============
            with gr.Tab("✏️ Editar Prompt"):
                
                gr.Markdown("### Seleccionar Prompt")
                
                with gr.Row():
                    edit_agent_type = gr.Dropdown(
                        choices=["Selecciona..."] + get_agent_types(),
                        value="Selecciona...",
                        label="Tipo de Agente",
                        scale=1
                    )
                    edit_prompt_name = gr.Dropdown(
                        choices=["Selecciona primero un agente..."],
                        value="Selecciona primero un agente...",
                        label="Nombre del Prompt",
                        scale=1,
                        interactive=True
                    )
                    load_btn = gr.Button("📂 Cargar Prompt", scale=1)
                
                version_info = gr.Markdown("")
                
                gr.Markdown("### Contenido del Prompt")
                
                prompt_editor = gr.Textbox(
                    label="Contenido del Prompt",
                    placeholder="Escribe o edita el prompt aquí...",
                    lines=15,
                    max_lines=30
                )
                
                with gr.Row():
                    description_input = gr.Textbox(
                        label="Descripción de cambios",
                        placeholder="Ej: Mejorado el tono de respuesta, agregado contexto sobre...",
                        lines=2,
                        scale=3
                    )
                    created_by_input = gr.Textbox(
                        label="Creado por",
                        value="admin",
                        scale=1
                    )
                
                auto_activate_check = gr.Checkbox(
                    label="✅ Activar automáticamente esta versión",
                    value=True
                )
                
                with gr.Row():
                    save_btn = gr.Button("💾 Guardar Nueva Versión", variant="primary", size="lg", scale=3)
                    clear_form_btn = gr.Button("🗑️ Limpiar Formulario", size="lg", scale=1)
                
                save_result = gr.Markdown("")
                
                history_display = gr.HTML("")
                
                edit_agent_type.change(
                    fn=get_prompt_names_for_agent,
                    inputs=edit_agent_type,
                    outputs=edit_prompt_name
                )
                
                load_btn.click(
                    fn=load_prompt_for_edit,
                    inputs=[edit_agent_type, edit_prompt_name],
                    outputs=[prompt_editor, version_info, history_display]
                )
                
                save_btn.click(
                    fn=save_new_version,
                    inputs=[
                        edit_agent_type,
                        edit_prompt_name,
                        prompt_editor,
                        description_input,
                        auto_activate_check,
                        created_by_input
                    ],
                    outputs=[save_result, prompts_display, prompt_editor, version_info, history_display]
                )
                
                clear_form_btn.click(
                    fn=clear_edit_form,
                    inputs=None,
                    outputs=[edit_agent_type, edit_prompt_name, prompt_editor, version_info, history_display]
                )
            
            # ============= TAB 4: HISTORIAL =============
            with gr.Tab("📜 Historial de Versiones"):
                
                gr.Markdown("### Ver Historial de Versiones")
                
                with gr.Row():
                    hist_agent_type = gr.Dropdown(
                        choices=["Selecciona..."] + get_agent_types(),
                        value="Selecciona...",
                        label="Tipo de Agente"
                    )
                    hist_prompt_name = gr.Dropdown(
                        choices=["Selecciona primero un agente..."],
                        value="Selecciona primero un agente...",
                        label="Nombre del Prompt"
                    )
                    hist_load_btn = gr.Button("📜 Ver Historial")
                
                history_html = gr.HTML(
                    value="<p style='color: #666;'>Selecciona un agente y prompt para ver el historial</p>"
                )
                
                gr.Markdown("### Activar Versión Específica")
                
                with gr.Row():
                    version_to_activate = gr.Number(
                        label="Número de versión",
                        value=1,
                        precision=0,
                        minimum=1
                    )
                    activate_btn = gr.Button("✅ Activar Versión", variant="primary")
                
                activate_result = gr.Markdown("")
                
                hist_agent_type.change(
                    fn=get_prompt_names_for_agent,
                    inputs=hist_agent_type,
                    outputs=hist_prompt_name
                )
                
                hist_load_btn.click(
                    fn=get_version_history,
                    inputs=[hist_agent_type, hist_prompt_name],
                    outputs=history_html
                )
                
                activate_btn.click(
                    fn=activate_version_by_id,
                    inputs=[hist_agent_type, hist_prompt_name, version_to_activate],
                    outputs=[activate_result, history_html]
                )

            # ============= TAB 5: EXPORTAR =============
            with gr.Tab("💾 Exportar Prompts"):
                
                gr.Markdown("""
                ### Exportar Todos los Prompts
                
                Genera un archivo `.txt` con todos los prompts activos, organizados por agente.
                Útil para:
                - 📋 Backup de configuración
                - 📤 Compartir prompts con Claude u otros asistentes
                - 📝 Documentación del sistema
                - 🔍 Debugging y análisis
                """)
                
                export_btn = gr.Button(
                    "💾 Exportar Todos los Prompts Activos",
                    variant="primary",
                    size="lg"
                )
                
                export_result = gr.Markdown("")
                
                download_file = gr.File(
                    label="📥 Descargar archivo exportado",
                    visible=True,
                    interactive=False
                )
                
                gr.Markdown("### Vista Previa")
                
                export_preview = gr.Textbox(
                    label="Contenido exportado (preview primeros 5000 caracteres)",
                    lines=20,
                    max_lines=30,
                    show_copy_button=True,
                    interactive=False
                )
                
                export_btn.click(
                    fn=export_all_prompts,
                    inputs=None,
                    outputs=[download_file, export_result]
                ).then(
                    fn=export_and_preview,
                    inputs=[download_file, export_result],
                    outputs=[download_file, export_result, export_preview]
                )

        gr.Markdown(
            """
            ---
            <div style='text-align: center; color: #666; font-size: 0.9em;'>
                💡 <strong>Tip:</strong> Cada vez que guardas, se crea una nueva versión. 
                Puedes volver a versiones anteriores en cualquier momento.<br>
                ⚡ <strong>Los cambios son inmediatos</strong> - No necesitas reiniciar Minerva.<br>
                🔄 <strong>Todos los datos se cargan dinámicamente de la base de datos</strong> - Sin valores hardcodeados.
            </div>
            """
        )
    
    return admin_interface


if __name__ == "__main__":
    print("Lanzando interfaz de administración de prompts...")
    interface = create_prompt_admin_interface()
    interface.launch(server_port=7861, share=False)