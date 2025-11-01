import os

def detect_product_with_ai():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    parent_dir = os.path.dirname(current_dir)
    config_path = os.path.join(parent_dir,"prompts//prompt_output.txt")

    try:
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as file:
                prompt = file.read()
                print("Se cargó correctamente el archivo.")
                return prompt  # Retorna el contenido del archivo
        else:
            print(f"El archivo {config_path} no existe.")
            return None
    except Exception as e:
        print(f"No se pudo cargar el archivo: {e}")
        return None  # Retorna None si ocurre algún error

# Ejecutar prueba
print("🔍 Buscando prompts en la carpeta actual...")
print("📍 Carpeta actual:", os.getcwd())

config = detect_product_with_ai()

if config is not None:
    print("\n📄 Contenido del prompts:")
    print(config)
else:
    print("\n🚨 No se pudo cargar la configuración.")
