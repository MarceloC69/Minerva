# scripts/init_prompts.py - Inicializa prompts desde archivo YAML
"""
Script para cargar prompts iniciales desde config/prompts.yaml a la base de datos.
Se ejecuta automáticamente la primera vez o manualmente cuando sea necesario.
"""

import sys
from pathlib import Path
import yaml
import logging

# Agregar directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.database.manager import DatabaseManager
from src.database.prompt_manager import PromptManager
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_prompts_from_yaml(yaml_path: Path) -> dict:
    """
    Carga prompts desde archivo YAML.
    
    Args:
        yaml_path: Ruta al archivo YAML
        
    Returns:
        Dict con prompts organizados por agente
    """
    try:
        with open(yaml_path, 'r', encoding='utf-8') as f:
            prompts = yaml.safe_load(f)
        
        logger.info(f"✅ Prompts cargados desde {yaml_path}")
        return prompts
        
    except Exception as e:
        logger.error(f"❌ Error cargando prompts: {e}")
        return {}


def initialize_prompts(force_reload: bool = False):
    """
    Inicializa prompts en la base de datos.
    
    Args:
        force_reload: Si True, recrea todos los prompts
    """
    logger.info("🚀 Inicializando sistema de prompts...")
    
    # Inicializar managers
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    prompt_manager = PromptManager(db_manager)
    
    # Cargar prompts desde YAML
    yaml_path = ROOT_DIR / "config" / "prompts.yaml"
    prompts_data = load_prompts_from_yaml(yaml_path)
    
    if not prompts_data:
        logger.error("❌ No se pudieron cargar prompts")
        return
    
    # Procesar cada agente
    created_count = 0
    skipped_count = 0
    
    for agent_type, prompts in prompts_data.items():
        logger.info(f"\n📝 Procesando prompts para: {agent_type}")
        
        for prompt_name, prompt_info in prompts.items():
            # Verificar si ya existe (solo si no es force_reload)
            if not force_reload:
                existing = prompt_manager.get_active_prompt(agent_type, prompt_name)
                if existing:
                    logger.info(f"  ⏭️  {prompt_name} ya existe (v activa)")
                    skipped_count += 1
                    continue
            
            # Crear nueva versión
            try:
                prompt_manager.create_prompt_version(
                    agent_type=agent_type,
                    prompt_name=prompt_name,
                    content=prompt_info['content'].strip(),
                    description=prompt_info.get('description', ''),
                    variables=prompt_info.get('variables', []),
                    created_by='init_script',
                    auto_activate=True
                )
                
                logger.info(f"  ✅ {prompt_name} creado y activado")
                created_count += 1
                
            except Exception as e:
                logger.error(f"  ❌ Error creando {prompt_name}: {e}")
    
    # Resumen
    logger.info("\n" + "="*60)
    logger.info(f"✅ Inicialización completada:")
    logger.info(f"   - Creados: {created_count}")
    logger.info(f"   - Omitidos: {skipped_count}")
    logger.info("="*60)


def list_all_prompts():
    """Lista todos los prompts activos en la base de datos."""
    logger.info("\n📋 Prompts activos en la base de datos:")
    logger.info("="*60)
    
    db_manager = DatabaseManager(db_path=settings.SQLITE_PATH)
    prompt_manager = PromptManager(db_manager)
    
    all_prompts = prompt_manager.get_all_active_prompts()
    
    if not all_prompts:
        logger.info("❌ No hay prompts activos")
        return
    
    for key, content in all_prompts.items():
        agent_type, prompt_name = key.split('.')
        logger.info(f"\n🤖 {agent_type} → {prompt_name}")
        logger.info(f"   {content[:100]}..." if len(content) > 100 else f"   {content}")
    
    logger.info("\n" + "="*60)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Gestiona prompts de Minerva")
    parser.add_argument(
        '--init',
        action='store_true',
        help='Inicializa prompts desde YAML'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Fuerza la recarga de todos los prompts'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='Lista todos los prompts activos'
    )
    
    args = parser.parse_args()
    
    if args.list:
        list_all_prompts()
    elif args.init:
        initialize_prompts(force_reload=args.force)
    else:
        parser.print_help()