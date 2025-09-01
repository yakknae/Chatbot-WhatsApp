from datetime import datetime
from fastapi import Depends, Request, APIRouter
from ..crud import verify_token
import os
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from ..schemas import SendMessageRequest
from ..crud import get_response

# Crear el router
router = APIRouter()

# Credenciales
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")

# Carpeta para conversaciones
CARPETA_CONVERSACIONES = "conversaciones"
os.makedirs(CARPETA_CONVERSACIONES, exist_ok=True)

# Lista para guardar mensajes recibidos en memoria
mensajes_recibidos = []

# Cliente de Twilio
client = Client(account_sid, auth_token)

@router.get("/test")
def test():
    return {"message": "Funciona!"}

# Enviar mensaje manualmente
@router.post("/send")
def send_whatsapp(request_data: SendMessageRequest, token: str = Depends(verify_token)):
    message = client.messages.create(
        from_=twilio_whatsapp_number,
        body=request_data.message,
        to=f"whatsapp:{request_data.to}"
    )
    return {"status": "success", "sid": message.sid}

# Recibir mensajes entrantes de WhatsApp
@router.post("/webhook")
async def webhook(request: Request):
    try:
        # Intentar obtener como form-data
        form_data = await request.form()
        from_number = form_data.get("From")
        body = form_data.get("Body")

        # Depuración: imprimir todo lo que llega
        print("Form data recibida:", form_data)

        # Guardar el mensaje en memoria si existen datos
        if not from_number or  not body:
            return{"error":"Datos incompletos","Status":"Failed"}

        mensaje = {"from": from_number, "body": body}
        mensajes_recibidos.append(mensaje)

        # Mostrar por consola
        print(f"📩 Mensaje recibido de {from_number}: {body}")

        # Guardar en archivo de texto
        # Normaliza el número para usarlo como nombre de archivo
        session_id = from_number.replace("whatsapp:", "").replace("+", "").replace(":", "_")
        ruta_archivo = os.path.join(CARPETA_CONVERSACIONES, f"{session_id}.txt")

        with open(ruta_archivo, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - De {from_number}: {body}\n")

        #  OBTENER RESPUESTA DEL BOT (con IA, base de datos, historial, etc.)
        try:
            bot_response = get_response(body)
        except Exception as e:
            print(f"❌ Error generando respuesta con IA: {e}")
            bot_response = "Lo siento, estoy teniendo problemas para responder. Intenta más tarde."

        # Guardar respuesta del bot en el archivo
        with open(ruta_archivo, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - Bot: {bot_response}\n")

        #  ENVIAR RESPUESTA POR WHATSAPP
        try:
            client.messages.create(
                from_=twilio_whatsapp_number,
                body=bot_response,
                to=from_number
            )
            print(f"✅ Respuesta enviada a {from_number}")
        except TwilioRestException as e:
            print(f"⚠ No se pudo enviar la respuesta automática: {e.msg}")

        return {"status": "ok", "reply_sent": True}


    except Exception as e:
        print(f"❌ Error procesando webhook: {str(e)}")
        return {"error": str(e)}

# Endpoint para ver mensajes en memoria
@router.get("/mensajes")
def ver_mensajes():
    return {"mensajes": mensajes_recibidos}
