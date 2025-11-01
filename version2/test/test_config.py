# test_config.py

import os
import json

def load_config():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    config_path = os.path.join(parent_dir,"config.json")

    try:
        with open(config_path, "r", encoding="utf-8") as file:
            print("✅ Archivo encontrado. Cargando contenido...")
            config = json.load(file)
            print("✅ config.json cargado correctamente.")
            return config
    except FileNotFoundError:
        print("❌ Error: El archivo config.json no fue encontrado.")
        return None
    except json.JSONDecodeError:
        print("❌ Error: El archivo config.json no es válido (JSON mal formado).")
        return None

# Ejecutar prueba
print("🔍 Buscando config.json en la carpeta actual...")
print("📍 Carpeta actual:", os.getcwd())

config = load_config()

if config is not None:
    print("\n📄 Contenido del config.json:")
    print(config)
else:
    print("\n🚨 No se pudo cargar la configuración.")