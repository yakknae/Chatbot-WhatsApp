# twilio_client.py
import os
from twilio.rest import Client

# Cargar credenciales
account_sid = os.getenv("TWILIO_ACCOUNT_SID")
auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_whatsapp_number = os.getenv("TWILIO_WHATSAPP_NUMBER")

# Validar que existan
if not all([account_sid, auth_token, twilio_whatsapp_number]):
    raise EnvironmentError("Faltan variables de entorno para Twilio: TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER")

# Crear cliente
client = Client(account_sid, auth_token)