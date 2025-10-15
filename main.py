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

from src.ui.chat_interface import create_interface


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
    
    # Crear y lanzar interfaz
    print("✅ Creando interfaz...")
    interface = create_interface()
    
    print("\n" + "="*60)
    print("🎉 Minerva está listo!")
    print("📱 Abre tu navegador en: http://localhost:7860")
    print("🛑 Presiona Ctrl+C para detener")
    print("="*60 + "\n")
    
    # Lanzar Gradio
    interface.launch(
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