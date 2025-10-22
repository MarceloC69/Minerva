#!/usr/bin/env python3
"""
Minerva - Asistente Personal Local con RAG
Punto de entrada principal para la aplicación.
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

import gradio as gr
from src.ui.chat_interface import create_interface as create_chat_interface
from src.ui.prompt_admin import create_prompt_admin_interface


def main():
    """Función principal que lanza la aplicación."""
    print("🚀 Iniciando Minerva...")
    print("📍 Verificando componentes...")
    
    # Verificar que Ollama está corriendo
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print("✅ Ollama conectado")
        else:
            print("⚠️  Ollama respondió pero con error")
    except Exception as e:
        print("❌ Error: Ollama no está corriendo")
        print("   Por favor ejecuta: ollama serve")
        return
    
    # Verificar directorios
    data_dir = ROOT_DIR / "data"
    data_dir.mkdir(exist_ok=True)
    (data_dir / "qdrant_storage").mkdir(exist_ok=True)
    (data_dir / "sqlite").mkdir(exist_ok=True)
    (data_dir / "uploads").mkdir(exist_ok=True)
    print("✅ Directorios verificados")
    
    # Crear interfaces
    print("✅ Creando interfaz de chat...")
    chat_interface = create_chat_interface()
    
    print("✅ Creando interfaz de administración...")
    admin_interface = create_prompt_admin_interface()
    
    print("✅ Creando placeholder de documentos...")
    # Crear interfaz de documentos (placeholder)
    with gr.Blocks() as docs_interface:
        gr.Markdown(
            """
            ## 📁 Gestión de Documentos
            
            Esta sección estará disponible en la siguiente fase.
            
            **Características planeadas:**
            - 📤 Subir documentos (PDF, TXT, DOCX, MD)
            - 📊 Ver estadísticas de indexación
            - 🗑️ Eliminar documentos
            - 🔄 Re-indexar colección
            - 📈 Métricas de uso
            
            ---
            
            *Por ahora, puedes gestionar prompts en la pestaña de Administración.*
            """
        )
    
    # Combinar interfaces usando TabbedInterface
    print("✅ Integrando componentes...")
    app = gr.TabbedInterface(
        interface_list=[chat_interface, admin_interface, docs_interface],
        tab_names=["💬 Chat", "⚙️ Administración", "📁 Documentos"],
        title="🧠 Minerva - Asistente Personal Local",
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            font=["Inter", "sans-serif"]
        ),
        css="""
        /* Container principal con scroll si es necesario */
        .gradio-container {
            max-width: 1400px !important;
            height: 100vh !important;
            overflow-y: auto !important;
            overflow-x: hidden !important;
        }
        
        /* Tabs más compactos */
        .tab-nav button {
            font-size: 1em !important;
            padding: 10px 20px !important;
        }
        
        /* Scroll personalizado para el container principal */
        .gradio-container::-webkit-scrollbar {
            width: 10px;
        }
        .gradio-container::-webkit-scrollbar-track {
            background: #f1f1f1;
        }
        .gradio-container::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 5px;
        }
        .gradio-container::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
        
        /* Para Firefox */
        .gradio-container {
            scrollbar-width: thin;
            scrollbar-color: #888 #f1f1f1;
        }
        
        /* Asegurar que el contenido no se salga horizontalmente */
        * {
            box-sizing: border-box;
        }
        """
    )
    
    print("\n" + "="*60)
    print("🎉 Minerva está listo!")
    print("📱 Abre tu navegador en: http://localhost:7860")
    print("")
    print("📑 Pestañas disponibles:")
    print("   💬 Chat - Conversa con Minerva")
    print("   ⚙️ Administración - Gestiona prompts de agentes")
    print("   📁 Documentos - (Próximamente)")
    print("")
    print("🛑 Presiona Ctrl+C para detener")
    print("="*60 + "\n")
    
    # Lanzar Gradio
    app.launch(
        server_name="0.0.0.0",  # Permite acceso desde la red local
        server_port=7860,
        share=False,  # Cambiar a True para generar link público temporal
        show_error=True,
        quiet=False
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Minerva se ha detenido. ¡Hasta luego!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)