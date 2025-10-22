#!/usr/bin/env python3
"""
Script para limpiar la memoria de hechos almacenados en Qdrant.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.memory.vector_store import VectorMemory
from config.settings import settings

def main():
    print("=" * 60)
    print("🧹 LIMPIEZA DE MEMORIA")
    print("=" * 60)
    
    print("\n⚠️  Esto eliminará TODOS los hechos almacenados en Qdrant")
    response = input("¿Estás seguro? (s/n): ")
    
    if response.lower() != 's':
        print("❌ Operación cancelada")
        return
    
    print("\n🗑️  Eliminando colección...")
    
    try:
        vm = VectorMemory(
            path=str(settings.QDRANT_STORAGE_PATH),
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vector_size=settings.EMBEDDING_DIM
        )
        
        # Ver info antes de eliminar
        try:
            info = vm.get_collection_info()
            print(f"\nColección actual:")
            print(f"  - Puntos: {info['points_count']}")
            print(f"  - Vectores: {info['vectors_count']}")
        except:
            pass
        
        # Eliminar
        vm.delete_collection()
        
        print("\n✅ Memoria limpiada exitosamente")
        print("\nℹ️  La colección se recreará automáticamente cuando:")
        print("   - Arranques Minerva")
        print("   - Se extraiga el primer hecho")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()