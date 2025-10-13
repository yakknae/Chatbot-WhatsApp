import os
import re
import json
from fastapi import HTTPException
from langchain_ollama import OllamaLLM
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.database import connect_to_db
from datetime import datetime
from .twilio_client import client, twilio_whatsapp_number
from collections import defaultdict

# ================================
# Verificar Token
# ================================
access_token_env = os.getenv("ACCESS_TOKEN")
def verify_token(token: str):
    if token != access_token_env:
        raise HTTPException(status_code=401, detail="Token inválido")
    return True

carritos = defaultdict(list)


# ================================
# Cargar configuración
# ================================

# Cargar el archivo config.json
def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as file:
            print("Archivo config.json cargado correctamente.")
            return json.load(file)
    except FileNotFoundError:
        print("Error: El archivo config.json no fue encontrado.")
        return None
    except json.JSONDecodeError:
        print("Error: El archivo config.json no es válido.")
        return None

# Cargar la configuración al inicio del programa
config = load_config()
if not config:
    exit("No se pudo cargar la configuración. Terminando el programa.")


# ================================
# Enviar mensaje al gerente una vez hecho el pedido
# ================================

# Enviar mensaje manualmente
from datetime import datetime

def send_order_summary_to_manager(order_data: dict, manager_number: str):
    try:
        lines = ["🛒 *¡Nuevo pedido recibido!*", ""]
        lines.append(f"*Cliente:* {order_data.get('cliente', 'WhatsApp')}")
        lines.append(f"*Teléfono:* {order_data.get('telefono', 'Desconocido')}")
        lines.append(f"*Fecha:* {order_data.get('fecha', datetime.now().strftime('%Y-%m-%d %H:%M'))}")
        lines.append("")
        lines.append("*Productos:*")
        
        total = 0
        for p in order_data.get("productos", []):
            nombre = p.get("nombre", "Producto")
            cantidad = p.get("cantidad", 1)
            precio = p.get("precio", 0)
            subtotal = cantidad * precio
            total += subtotal
            lines.append(f"  • {cantidad}x {nombre} - ${subtotal}")
        
        lines.append("")
        lines.append(f"*TOTAL: ${total}*")
        
        message_body = "\n".join(lines)
        
        message = client.messages.create(
            from_=twilio_whatsapp_number,
            body=message_body,
            to=f"whatsapp:{manager_number}"
        )
        print(f"✅ Pedido enviado al gerente. SID: {message.sid}")
        return True
    except Exception as e:
        print(f"❌ Error al enviar pedido: {e}")
        return False



# ================================
# Modelo de IA
# ================================

# Configuración inicial del modelo Ollama
model = OllamaLLM(model="gemma3:latest")

# Prompt con historial
prompt = ChatPromptTemplate.from_messages([
    ("system", "Eres un asistente útil."),
    MessagesPlaceholder(variable_name="history"),
    ("human", "{input}")
])

# Cadena final
chain = prompt | model

# Historial en memoria
store = {}

def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

with_message_history = RunnableWithMessageHistory(
    chain,
    get_session_history,
    input_messages_key="input",
    history_messages_key="history"
)

def cargar_historial_para_ia(session_id: str) -> str:
    ruta = os.path.join("conversaciones", f"{session_id}.txt")
    print(ruta)
    if not os.path.exists(ruta):
        return "No hay historial disponible."

    try:
        with open(ruta, "r", encoding="utf-8") as f:
            lineas = f.readlines()

        conversacion = []
        for linea in lineas:
            if " - De " in linea:
                try:
                    contenido = linea.split(" - De ")[1].split(": ", 1)[1].strip()
                    conversacion.append(f"Usuario: {contenido}")
                except:
                    continue
            elif " - Bot: " in linea:
                try:
                    contenido = linea.split(" - Bot: ", 1)[1].strip()
                    conversacion.append(f"Bot: {contenido}")
                except:
                    continue
        
        return "\n".join(conversacion)
    
    except Exception as e:
        return "Error al leer el historial."

# ================================
# Buscar productos
# ================================

def get_product_info(product_name: str):
    connection = connect_to_db()
    if not connection:
        return print("no se conecto a la bd")
    else:
        print("se conecto a la bd")

    cursor = connection.cursor(dictionary=True)
    # Consulta para productos que COMIENZAN con el nombre dado
    QUERY_START = """SELECT 
    p.id, 
    p.nombre AS producto, 
    p.descripcion, 
    p.precio_costo, 
    p.precio_venta, 
    p.stock, 
    m.nombre AS marca, 
    c.nombre AS categoria
    FROM productos p 
    INNER JOIN marcas m ON p.marca_id = m.id 
    INNER JOIN categorias c ON p.categoria_id = c.id
    WHERE LOWER(p.nombre) LIKE %s or LOWER(m.nombre) LIKE %s or LOWER(c.nombre) LIKE %s
    ORDER BY p.nombre ASC; """

    # Consulta para productos que CONTIENEN el nombre dado

    QUERY_CONTAINS = """SELECT 
    p.id, 
    p.nombre AS producto, 
    p.descripcion, 
    p.precio_costo, 
    p.precio_venta, 
    p.stock, 
    m.nombre AS marca, 
    c.nombre AS categoria
    FROM productos p 
    INNER JOIN marcas m ON p.marca_id = m.id 
    INNER JOIN categorias c ON p.categoria_id = c.id
    WHERE LOWER(p.nombre) LIKE %s
    AND NOT LOWER(p.nombre) LIKE %s
    ORDER BY p.nombre ASC;"""

    product_name_lower = product_name.strip().lower()

    words = product_name.strip().lower().split()
    if words:
        first_word = words[0]
    else:
        first_word = product_name.strip().lower()

    # Usar la consulta externa
    cursor.execute(QUERY_START, (f"{first_word}%",f"{first_word}%",f"{first_word}%"))
    start_results = cursor.fetchall()

    if start_results:
        cursor.close()
        connection.close()
        return start_results

    # Si no hay coincidencias al inicio, buscar que contenga el término
    cursor.execute(QUERY_CONTAINS, (f"%{product_name_lower}%", f"{product_name_lower}%"))
    contain_results = cursor.fetchall()

    cursor.close()
    connection.close()

    if contain_results:
        return contain_results

    return f"No se encontró ningún producto relacionado con '{product_name}'."

# ================================
# Detectar producto con IA
# ================================

def detect_product_with_ai(user_input):
    with open("prompts//prompt_input.txt", "r", encoding="utf-8") as file:
        prompt = file.read()
        print("Se cargó correctamente el archivo.txt")
    
    prompt += f"""

Frase del usuario: "{user_input}"
Producto mencionado: 
"""
    try:
        # Invocar al modelo
        raw_response = model.invoke(prompt).strip()

        # Limpiar la respuesta
        # Eliminar etiquetas <think>...<think>
        cleaned = re.sub(r"<think>.*?</think>", "", raw_response, flags=re.DOTALL | re.IGNORECASE)
        
        # Extraer la parte después de "Productos mencionados:"
        if "Productos mencionados:" in cleaned:
            products_text = cleaned.split("Productos mencionados:")[1].strip()
        else:
            products_text = cleaned  # por si el modelo responde directamente

        # Divide por coma, " y ", o saltos de línea
        product_list = re.split(r',|\s+y\s+|\n', products_text, flags=re.IGNORECASE)
        
        # Limpiar cada producto
        product_list = [
            p.strip().rstrip(".").strip()
            for p in product_list
            if p.strip() and p.lower() not in ["ninguno", "ninguna", "no"]
        ]

        # Validar que no esté vacío
        if not product_list:
            return None

        print(f"✅ Productos detectados: {product_list}")
        return product_list  # Devuelve lista

    except Exception as e:
        print(f"❌ Error en detect_product_with_ai: {e}")
        return None

# ================================
# Obtener respuesta del bot
# ================================

def get_response(user_input: str, session_id: str) -> str:
    user_input_lower = user_input.lower().strip()
    
    # 1. Detectar producto con IA
    detected_product = detect_product_with_ai(user_input)
    all_products = []
    if detected_product:
        print(f"Producto detectado (caso 1 ): {detected_product}")
        for product_name in detected_product:
            products = get_product_info(product_name)
            if isinstance(products,list):
                all_products.extend(products)
        products = all_products
    else:
        print("Ningún producto detectado.")
        products = []

    # === NUEVO: Si el usuario quiere agregar productos al carrito ===
    palabras_agregar = ["agregar", "agregá", "añadir", "poner", "incluir", "sumar"]
    if any(palabra in user_input_lower for palabra in palabras_agregar) and products:
        # Guardar productos en el carrito de esta sesión
        carritos[session_id].extend(products)
        return f"✅ Productos agregados al carrito. Tienes {len(carritos[session_id])} producto(s)."
    
    # === NUEVO: Si el usuario pide ver el carrito ===
    palabras_carrito = ["carrito", "pedido", "comprar", "ordenar", "quiero comprar", "hacer pedido", "ver carrito", "mostrar carrito"]
    if any(palabra in user_input_lower for palabra in palabras_carrito):
        if carritos[session_id]:
            # Mostrar resumen del carrito
            resumen = "🛒 Tu carrito:\n"
            total = 0
            for p in carritos[session_id]:
                name = p.get('producto', 'Producto')
                price = p.get('precio_venta', 0)
                resumen += f"- {name} - ${price}\n"
                total += price
            resumen += f"\nTotal: ${total}\n\n¿Deseas confirmar este pedido? Responde *sí* para finalizar."
            return resumen
        else:
            return "No tienes productos en el carrito. ¿Qué te gustaría comprar?"

    # === NUEVO: Confirmar pedido ===
    palabras_confirmar = ["sí", "si", "confirmo", "acepto", "quiero", "comprar", "finalizar", "ordenar"]
    if (
        any(palabra in user_input_lower for palabra in palabras_confirmar) 
        and len(user_input_lower.split()) <= 5
        and carritos[session_id]  # ← ahora usamos el carrito, no products
    ):
        # Construir datos del pedido
        order_data = {
            "cliente": "Cliente WhatsApp",
            "telefono": session_id.replace("whatsapp:", ""),
            "productos": [
                {
                    "nombre": p.get("producto", "Producto"),
                    "cantidad": 1,
                    "precio": p.get("precio_venta", 0)
                }
                for p in carritos[session_id]
            ],
            "fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
        }

        # Enviar al gerente
        MANAGER_NUMBER = "+5491112345678"
        send_order_summary_to_manager(order_data, MANAGER_NUMBER)

        # Limpiar carrito después de enviar
        carritos[session_id].clear()

        return "¡Pedido confirmado! 🎉 El gerente ha sido notificado y se comunicará contigo pronto."

    # 1,5 . Si hay productos encontrados
    if products:
        context = "Tenemos estos tipos de productos disponibles:\n"
        for product in products:
            stock_status = "Disponible" if product.get("stock", 0) > 0 else "Agotado"
            name = product.get('producto', 'Producto sin nombre')
            description = product.get('descripcion', 'Sin descripción')
            brand = product.get('marca', 'Marca desconocida')
            price = product.get('precio_venta', 'Precio no disponible')
            category = product.get('categoria', 'Categoría desconocida')

            context += (
                f"- **{name}**\n"
                f"  - Descripción: {description}\n"
                f"  - Marca: {brand}\n"
                f"  - Categoría: {category}\n"
                f"  - Precio: ${price}\n"
                f"  - Stock: {product.get('stock', 0)} unidades ({stock_status})\n\n"
            )

        full_prompt = f"""
        {context}
        El usuario pregunta: "{user_input}"
        Respuesta clara y amigable:
        """
        try:
            result = with_message_history.invoke(
                {"input": full_prompt},
                config={"configurable": {"session_id": session_id}}
            )
            #  Aseguramos que sea string, sin depender de .content
            bot_response = result.content if hasattr(result, "content") else str(result)
            return bot_response.strip()
        except Exception as e:
            print(f"❌ Error al generar respuesta (productos): {e}")
            return "No pude procesar esa consulta. Intenta más tarde."


    
    # 2. Si NO se encontró ningún producto → analizar si es una comida compuesta
    else:
        prompt_ingredientes = f"""
Analiza si '{user_input}' es un plato o comida compuesta (como ensalada, torta, sándwich, etc.).
Si lo es, responde SOLO con los nombres de los ingredientes principales separados por comas.
Si no, responde exactamente: "ninguno"

Ejemplos:
- Entrada: "ensalada"
  Salida: lechuga, tomate, pepino, zanahoria, aceitunas

- Entrada: "torta de chocolate"
  Salida: harina, azúcar, huevos, cacao en polvo, manteca

- Entrada: "leche"
  Salida: ninguno

- Entrada: "hamburguesa"
  Salida: pan, carne molida, lechuga, tomate, queso

Entrada: "{user_input}"
Salida: 
"""

        try:
            raw_response = model.invoke(prompt_ingredientes).strip()
            print(f"🔍 Respuesta cruda de IA (ingredientes): {raw_response}")

            # Limpiar respuesta
            if "ninguno" in raw_response.lower():
                # No es un plato compuesto
                pass  # Continúa al siguiente paso
            else:
                ingredientes = [item.strip() for item in raw_response.split(",") if item.strip()]
                
                if ingredientes:
                    print(f"🍳 Ingredientes detectados: {ingredientes}")
                    
                    # Buscar cada ingrediente en la BD
                    productos_encontrados = []
                    for ingrediente in ingredientes:
                        resultado = get_product_info(ingrediente)
                        if isinstance(resultado, list):
                            productos_encontrados.extend(resultado)

                    if productos_encontrados:
                        context = f"Para preparar '{user_input}', tenemos estos ingredientes disponibles:\n"
                        for product in productos_encontrados:
                            stock_status = "Disponible" if product.get("stock", 0) > 0 else "Agotado"
                            name = product.get('producto', 'Producto sin nombre')
                            brand = product.get('marca', 'Marca desconocida')
                            price = product.get('precio_venta', 'Precio no disponible')

                            context += (
                                f"- **{name}** (Marca: {brand}) - Precio: ${price}, Stock: {product.get('stock', 0)} unidades ({stock_status})\n"
                            )

                        full_prompt = f"""
                        {context}
                        El usuario quiere preparar: "{user_input}"
                        Respuesta clara y amigable:
                        """
                        try:
                            result = with_message_history.invoke(
                                {"input": full_prompt},
                                config={"configurable": {"session_id": session_id}}
                            )
                            bot_response = result.content if hasattr(result, "content") else str(result)
                            return bot_response.strip()
                        except Exception as e:
                            print(f"❌ Error generando respuesta para comida compuesta: {e}")
                            return "Encontré algunos ingredientes, pero tuve problemas para responder."
                    else:
                        return f"No tenemos disponibles los ingredientes típicos para '{user_input}'."
        
        except Exception as e:
            print(f"❌ Error al descomponer comida compuesta: {e}")

    # 3. Respuesta predeterminada
    try:
        # Leer el contexto base del sistema desde archivo
        with open("prompts/prompt_output.txt", "r", encoding="utf-8") as fileOut:
            promptOutput = fileOut.read().strip()
            
    except Exception as e:
        print(f"❌ No se pudo leer prompt_output.txt: {e}")
        promptOutput = "Eres un asistente útil. Responde de forma amable y clara."
    print(promptOutput)

    system_context = promptOutput

    # Construye el input limpio → solo lo que dice el usuario
    final_input = f"{system_context}\n\nPregunta del usuario: {user_input}"
    print("variable final_input:", final_input)
    try:
        result = with_message_history.invoke(
            {"input": final_input},
            config={"configurable": {"session_id": session_id}}
        )
        bot_response = result.content if hasattr(result, "content") else str(result)
        return bot_response.strip()
    except Exception as e:
        print(f"❌ Error al generar respuesta predeterminada: {e}")
        return "Estoy teniendo problemas para responder."