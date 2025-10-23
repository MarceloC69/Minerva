# main.py
"""
Punto de entrada principal de Minerva.
Versión 2.1.0 - Con CrewAI + Mem0
"""

import os
import sys
import logging
from pathlib import Path

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Imports
from config.settings import settings
from src.ui.chat_interface import create_interface as create_chat_interface
from src.ui.prompt_admin import create_prompt_admin_interface


def verify_ollama():
    """Verifica que Ollama esté corriendo."""
    import requests
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            logger.info("✅ Ollama está corriendo")
            return True
    except:
        pass
    
    logger.error("❌ Ollama NO está corriendo")
    logger.error("   Ejecuta: ollama serve")
    return False


def verify_model():
    """Verifica que el modelo esté descargado."""
    import requests
    try:
        response = requests.get(f"{settings.OLLAMA_BASE_URL}/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            # Buscar el modelo (con o sin :latest)
            model_found = False
            for name in model_names:
                if settings.OLLAMA_MODEL in name or name in settings.OLLAMA_MODEL:
                    model_found = True
                    logger.info(f"✅ Modelo {name} disponible")
                    break
            
            if not model_found:
                logger.error(f"❌ Modelo {settings.OLLAMA_MODEL} NO encontrado")
                logger.error(f"   Modelos disponibles: {', '.join(model_names)}")
                logger.error(f"   Descarga con: ollama pull phi3")
                return False
            
            return True
    except Exception as e:
        logger.error(f"❌ Error verificando modelo: {e}")
        return False


def main():
    """Función principal."""
    try:
        logger.info("🚀 Iniciando Minerva v2.1.0...")
        
        # Verificaciones
        if not verify_ollama():
            sys.exit(1)
        
        if not verify_model():
            sys.exit(1)
        
        # Crear interfaz Gradio
        logger.info("🎨 Creando interfaz Gradio...")
        
        # FIX: NO usar 'with', solo llamar las funciones
        chat_ui = create_chat_interface()
        admin_ui = create_prompt_admin_interface()
        
        # Crear app completa
        import gradio as gr
        
        app = gr.TabbedInterface(
            [chat_ui, admin_ui],
            ["💬 Chat", "⚙️ Admin Prompts"],
            title="🧠 Minerva - Asistente Personal Local",
            theme=gr.themes.Soft()
        )
        
        # Lanzar
        logger.info("✅ Minerva lista")
        logger.info(f"🌐 Abriendo en: http://localhost:{settings.GRADIO_PORT}")
        
        app.launch(
            server_name="0.0.0.0",
            server_port=settings.GRADIO_PORT,
            share=False,
            show_error=True
        )
    
    except KeyboardInterrupt:
        logger.info("\n👋 Minerva cerrada por usuario")
    
    except Exception as e:
        logger.error(f"❌ Error fatal: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()