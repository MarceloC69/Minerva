# init_web_prompts.py - v1.0.0
"""
Script para inicializar prompts del WebAgent en Minerva.
Ejecuta este script después de integrar búsqueda web.
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent
sys.path.insert(0, str(ROOT_DIR))

from src.database.manager import DatabaseManager
from src.database.prompt_manager import PromptManager
from config.settings import settings


def initialize_web_prompts():
    """Crea los prompts por defecto para el WebAgent."""
    
    print("🔧 Inicializando PromptManager...")
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    pm = PromptManager(db_manager=db_manager)
    
    print("\n📝 Creando prompts para WebAgent...\n")
    
    # ========================================================================
    # AGENTE WEB - SYSTEM PROMPT
    # ========================================================================
    
    web_system = """Eres Minerva en modo de búsqueda web. Tu trabajo es sintetizar información de internet de forma clara y precisa.

DIRECTRICES IMPORTANTES:
1. **Resume información** de los resultados de búsqueda proporcionados
2. **Sé directo y conciso** - responde exactamente lo que se pregunta
3. **NO inventes** información que no esté en los resultados
4. **Menciona contradicciones** si las hay entre fuentes
5. **NO hagas sugerencias adicionales** a menos que se te pidan explícitamente
6. Si los resultados no son suficientes para responder, dilo claramente

FORMATO DE RESPUESTA:
- Responde directamente la pregunta del usuario
- Usa la información más reciente y relevante
- Estructura con bullets o párrafos según sea apropiado
- Sé natural, no uses frases como "según los resultados..." innecesariamente

EVITA:
- Sugerencias no solicitadas como "¿Te gustaría saber más sobre..."
- Repetir la pregunta del usuario
- Agregar información no relevante
- Ser demasiado verboso

Ejemplo BUENO:
Usuario: "¿Cuál es la temperatura en Buenos Aires?"
Respuesta: "La temperatura actual en Buenos Aires es de 24°C, con cielo parcialmente nublado."

Ejemplo MALO:
Usuario: "¿Cuál es la temperatura en Buenos Aires?"
Respuesta: "Basándome en los resultados de búsqueda, puedo decirte que la temperatura en Buenos Aires es de 24°C. ¿Te gustaría saber el pronóstico para los próximos días?"
"""
    
    pm.create_prompt_version(
        agent_type="web",
        prompt_name="system_prompt",
        content=web_system,
        description="Prompt del sistema para WebAgent - versión inicial",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt web.system_prompt creado")
    
    # ========================================================================
    # AGENTE WEB - SYNTHESIS PROMPT
    # ========================================================================
    
    web_synthesis = """Sintetiza la siguiente información de búsqueda web para responder la pregunta del usuario.

RESULTADOS DE BÚSQUEDA:
{search_results}

PREGUNTA DEL USUARIO:
{user_question}

INSTRUCCIONES:
- Usa solo la información de los resultados
- Sé directo y específico
- No repitas información
- No agregues sugerencias
- Si hay información contradictoria, mencionalo brevemente

RESPUESTA:"""
    
    pm.create_prompt_version(
        agent_type="web",
        prompt_name="synthesis_prompt",
        content=web_synthesis,
        description="Template para sintetizar resultados de búsqueda",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt web.synthesis_prompt creado")
    
    # ========================================================================
    # ROUTER - ACTUALIZADO PARA INCLUIR WEB
    # ========================================================================
    
    router_prompt_updated = """Analiza la siguiente pregunta del usuario y determina qué agente debe responderla.

PREGUNTA: {question}

¿Hay documentos disponibles?: {has_documents}

AGENTES DISPONIBLES:
1. WEB - Para información actualizada, noticias, clima, eventos recientes, precios actuales
2. KNOWLEDGE - Para preguntas sobre documentos indexados
3. CONVERSATIONAL - Para chat general, preguntas personales, opiniones

CRITERIOS DE DECISIÓN:

→ WEB si:
  - Pregunta sobre información actualizada (hoy, ahora, actual, reciente)
  - Consulta sobre noticias, clima, eventos deportivos
  - Precios actuales, cotizaciones, bolsa
  - Menciona fechas recientes o "últimas"
  - Pregunta que requiere datos actualizados de internet

→ KNOWLEDGE si:
  - Pregunta específica sobre documentos ("¿qué dice el documento sobre...")
  - Consulta sobre contenido indexado
  - Hay documentos disponibles Y la pregunta es relevante a ellos

→ CONVERSATIONAL si:
  - Chat casual, saludos, despedidas
  - Preguntas generales que no requieren info actualizada
  - Opiniones, consejos, explicaciones generales
  - Preguntas personales sobre preferencias

RESPONDE:
AGENT: [web/knowledge/conversational]
CONFIDENCE: [high/medium/low]
REASON: [breve explicación]"""
    
    pm.create_prompt_version(
        agent_type="router",
        prompt_name="routing_prompt",
        content=router_prompt_updated,
        description="Prompt actualizado con soporte para WebAgent",
        created_by="init_script",
        auto_activate=True
    )
    print("✅ Prompt router.routing_prompt actualizado")
    
    # ========================================================================
    # RESUMEN
    # ========================================================================
    
    print("\n" + "="*60)
    print("✅ Inicialización completa")
    print("="*60)
    print("\nPrompts creados/actualizados:")
    print("  • web.system_prompt")
    print("  • web.synthesis_prompt")
    print("  • router.routing_prompt (actualizado)")
    print("\nPuedes editarlos desde la UI de administración en:")
    print("  http://localhost:7860 → Pestaña 'Administración'")
    print("\nEl WebAgent ya está listo para usar.")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        print("🚀 Inicializando prompts de WebAgent...\n")
        initialize_web_prompts()
        print("🎉 ¡Listo! Minerva ahora puede buscar en internet.\n")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)