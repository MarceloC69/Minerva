#!/usr/bin/env python3
"""
Script para inicializar el prompt del fact_extractor en la base de datos.
Ejecutar solo UNA vez.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))



from src.database import DatabaseManager
from src.database.prompt_manager import PromptManager
from config.settings import settings

EXTRACTION_PROMPT = """Analiza la siguiente conversación y extrae SOLO hechos importantes sobre el usuario que deberían recordarse para futuras conversaciones.

REGLAS:
- Extrae SOLO información que sea relevante recordar (preferencias, gustos, información personal, contexto importante)
- NO extraigas información trivial o temporal
- Cada hecho debe ser una oración clara y concisa
- Categoriza cada hecho: [preferencia, personal, profesional, interes, contexto]

Conversación:
{conversation}

Responde SOLO con un JSON válido en este formato:
{{
  "facts": [
    {{"category": "preferencia", "fact": "Le gusta el cine de ciencia ficción"}},
    {{"category": "personal", "fact": "Vive en Guernica, Buenos Aires"}},
    {{"category": "profesional", "fact": "Es desarrollador Python"}}
  ]
}}

Si NO hay hechos importantes que extraer, responde:
{{"facts": []}}

JSON:"""

def main():
    """Inicializa el prompt de fact_extractor."""
    print("=" * 60)
    print("Inicializando prompt de fact_extractor")
    print("=" * 60)
    
    # Conectar a DB
    db = DatabaseManager(db_path=settings.SQLITE_PATH)
    pm = PromptManager(db)
    
    # Verificar si ya existe
    try:
        existing = pm.get_active_prompt('fact_extractor', 'extraction_prompt')
        if existing:
            print("\n⚠️  El prompt ya existe en la base de datos")
            print(f"Versión actual: {existing[:100]}...")
            
            response = input("\n¿Quieres actualizarlo? (s/n): ")
            if response.lower() != 's':
                print("❌ Operación cancelada")
                return
    except:
        pass
    
    # Crear/Actualizar prompt
    try:
        pm.create_prompt_version(
            agent_type='fact_extractor',
            prompt_name='extraction_prompt',
            content=EXTRACTION_PROMPT,
            description='Prompt para extraer hechos de conversaciones',
            created_by='system',
            auto_activate=True
        )
        print("\n✅ Prompt de fact_extractor creado correctamente")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verificar
    prompt = pm.get_active_prompt('fact_extractor', 'extraction_prompt')
    print(f"\n📝 Prompt almacenado (primeras 200 chars):")
    print("-" * 60)
    print(prompt[:200] + "...")
    print("-" * 60)
    
    print("\n✅ ¡Listo! El prompt está disponible en la base de datos")
    print("=" * 60)

if __name__ == "__main__":
    main()