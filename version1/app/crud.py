import os
import re
from fastapi import HTTPException
from langchain_ollama import OllamaLLM
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from app.database import connect_to_db
from collections import defaultdict
from datetime import datetime



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
# Modelo de IA
# ================================

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

# ================================
# Manejo de historial por sesión
# ================================

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

# ================================
# Enviar resumen de pedido al gerente
# ================================

def send_order_summary_to_manager(order_data: dict, manager_number: str):
    try:
        # Ruta del archivo de pedidos
        ruta_pedidos = os.path.join("conversaciones", "pedidos_pendientes.txt")
        
        # Formato del mensaje
        lines = [f"\n{'='*60}"]
        lines.append(f"📅 Fecha: {order_data.get('fecha', 'Sin fecha')}")
        lines.append(f"📱 Cliente: {order_data.get('telefono', 'Desconocido')}")
        lines.append(f"🛒 Productos:")
        
        total = 0
        for p in order_data.get("productos", []):
            nombre = p.get("nombre", "Producto")
            cantidad = p.get("cantidad", 1)
            precio = p.get("precio", 0)
            subtotal = cantidad * precio
            total += subtotal
            lines.append(f"   • {cantidad}x {nombre} → ${subtotal}")
        
        lines.append(f"💰 TOTAL: ${total}")
        lines.append(f"📞 Notificar al gerente: {manager_number}")
        lines.append(f"{'='*60}\n")
        
        mensaje_completo = "\n".join(lines)
        
        # Guardar en archivo
        with open(ruta_pedidos, "a", encoding="utf-8") as f:
            f.write(mensaje_completo)
        
        print("✅ Pedido guardado en 'conversaciones/pedidos_pendientes.txt'")
        return True
    except Exception as e:
        print(f"❌ Error al guardar pedido: {e}")
        return False



# ================================
# Detectar intención
# ================================

def detectar_intencion(user_input: str) -> str:
    """
    Devuelve una de: 'agregar', 'ver_carrito', 'confirmar', 'vaciar', 'ninguna'
    """
    prompt_intencion = f"""
Analiza el siguiente mensaje del usuario y responde ÚNICAMENTE con una de estas palabras:
- agregar
- ver_carrito
- confirmar
- vaciar
- ninguna

Reglas:
- Solo responde "agregar" si el usuario quiere AÑADIR un producto al carrito de compras.
- Solo responde "ver_carrito" si pide ver, mostrar o consultar su carrito o pedido actual.
- Solo responde "confirmar" si dice que quiere confirmar, finalizar, enviar, comprar o aceptar el pedido.
- Solo responde "vaciar" si dice que quiere vaciar, limpiar, borrar o empezar de nuevo el carrito.
- Frases como "me gusta el café", "quiero hacer una torta con dulce de leche", o "tienen leche?" NO son "agregar".
- Si no hay intención clara de interactuar con el carrito, responde "ninguna".

Mensaje: "{user_input}"
Respuesta:
"""
    try:
        respuesta = model.invoke(prompt_intencion).strip().lower()
        if respuesta in ["agregar", "ver_carrito", "confirmar", "vaciar"]:
            return respuesta
        else:
            return "ninguna"
    except Exception as e:
        print(f"❌ Error al detectar intención: {e}")
        return "ninguna"
    
def is_cart_related(user_input: str) -> bool:
    """
    Usa el prompt de carrito.txt para verificar si el mensaje
    expresa intención real de interactuar con el carrito.
    Devuelve True si la respuesta es "sí", False si es "no".
    """
    try:
        # Leer el prompt base
        with open("carrito.txt", "r", encoding="utf-8") as f:
            base_prompt = f.read().strip()
        
        # Formar el prompt completo
        full_prompt = base_prompt.replace("{user_input}", user_input)
        
        # Invocar al modelo (asumimos que with_message_history está disponible)
        result = with_message_history.invoke(
            {"input": full_prompt},
            config={"configurable": {"session_id": "temp_session_for_cart_check"}}
        )
        response = result.content.strip().lower() if hasattr(result, "content") else str(result).strip().lower()
        
        return "sí" in response or "si" in response  # maneja ambas formas
    except Exception as e:
        print(f"⚠️ Error al validar intención de carrito: {e}")
        # En caso de error, ser conservador: asumir que NO es intención de carrito
        return False
    

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
        print("Se cargó correctamente el prompt_input.txt")
    
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

        # Dividir por comas, saltos de línea o "y"

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
# respuesta del bot
# ================================

def get_response(user_input: str, session_id: str) -> str:
    user_input_lower = user_input.lower().strip()
    
    # 1. Detectar producto con IA
    detected_product = detect_product_with_ai(user_input)
    all_products = []
    if detected_product:
        print(f"Producto detectado: {detected_product}")
        for product_name in detected_product:
            products = get_product_info(product_name)
            if isinstance(products, list):
                all_products.extend(products)
        products = all_products
    else:
        print("Ningún producto detectado.")
        products = []

    # === Validar si hay intención real de interactuar con el carrito ===
    cart_intent = is_cart_related(user_input)

    # === AGREGAR al carrito ===
    palabras_agregar = ["agregar", "agregá", "añadir", "poner", "incluir", "sumar"]
    if (
        cart_intent and
        any(palabra in user_input_lower for palabra in palabras_agregar) and 
        products
    ):
        carritos[session_id].extend(products)
        return f"✅ Productos agregados al carrito. Tienes {len(carritos[session_id])} producto(s)."

    # === VER carrito ===
    palabras_carrito = ["carrito", "pedido", "comprar", "ordenar", "quiero comprar", "hacer pedido", "ver carrito", "mostrar carrito"]
    if cart_intent and any(palabra in user_input_lower for palabra in palabras_carrito):
        if carritos[session_id]:
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

    # === CONFIRMAR pedido ===
    palabras_confirmar = ["sí", "si", "confirmo", "acepto", "quiero", "comprar", "finalizar", "ordenar"]
    if (
        cart_intent and
        any(palabra in user_input_lower for palabra in palabras_confirmar) and
        len(user_input_lower.split()) <= 5 and
        carritos[session_id]
    ):
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

        MANAGER_NUMBER = "+5491112345678"
        send_order_summary_to_manager(order_data, MANAGER_NUMBER)
        carritos[session_id].clear()

        return "¡Pedido confirmado! 🎉 El gerente ha sido notificado y se comunicará contigo pronto."

    # ───────────────────────────────────────────────
    # A PARTIR DE ACÁ: NO ES INTERACCIÓN DE CARRITO
    # ───────────────────────────────────────────────

    # 2. Si HAY productos detectados → responder con contexto de productos
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
            bot_response = result.content if hasattr(result, "content") else str(result)
            return bot_response.strip()
        except Exception as e:
            print(f"❌ Error al generar respuesta (productos): {e}")
            return "No pude procesar esa consulta. Intenta más tarde."

    # 3. Si NO hay productos → intentar interpretar como comida compuesta
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

        if "ninguno" not in raw_response.lower():
            ingredientes = [item.strip() for item in raw_response.split(",") if item.strip()]
            if ingredientes:
                print(f"🍳 Ingredientes detectados: {ingredientes}")
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
                            f"- **{name}** (Marca: {brand}) - Precio: ${price}, "
                            f"Stock: {product.get('stock', 0)} unidades ({stock_status})\n"
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

    # 4. Respuesta predeterminada con contexto del sistema
    try:
        with open("prompts/prompt_output.txt", "r", encoding="utf-8") as fileOut:
            promptOutput = fileOut.read().strip()
    except Exception as e:
        print(f"❌ No se pudo leer prompt_output.txt: {e}")
        promptOutput = "Eres un asistente útil. Responde de forma amable y clara."

    print("Prompt del sistema cargado:", promptOutput)

    final_input = f"{promptOutput}\n\nPregunta del usuario: {user_input}"
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