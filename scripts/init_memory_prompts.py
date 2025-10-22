"""Inicializa los prompts de memoria en la base de datos."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database import DatabaseManager
from src.database.prompt_manager import PromptManager
from config.settings import settings


def init_memory_prompts():
    """Inicializa prompts de memoria."""
    
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    prompt_manager = PromptManager(db_manager)
    
    # Prompt para extraer hechos
    fact_extraction_prompt = """Eres un extractor de hechos. Analiza la siguiente conversación y extrae SOLO hechos importantes sobre el usuario.

REGLAS IMPORTANTES:
- NO uses numeración (1., 2., etc.)
- NO uses guiones ni bullets
- Escribe cada hecho en UNA línea
- Sé conciso y claro
- Si no hay hechos, responde "NINGUNO"

Ejemplos de buenos hechos:
El usuario se llama Juan
El usuario trabaja como ingeniero
Al usuario le gusta el jazz
El usuario vive en Madrid

Conversación:
{text}

Hechos sobre el usuario:"""
    
    # Guardar en DB usando create_prompt_version (método real)
    try:
        new_prompt = prompt_manager.create_prompt_version(
            agent_type='memory',
            prompt_name='fact_extraction',
            content=fact_extraction_prompt,
            description='Prompt para extraer hechos de conversaciones',
            variables=['text'],
            created_by='system',
            auto_activate=True
        )
        print(f"✅ Prompt de memoria creado con ID: {new_prompt.id}, versión: {new_prompt.version}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    init_memory_prompts()