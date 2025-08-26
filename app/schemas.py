from pydantic import BaseModel


# Modelo para enviar mensajes
class SendMessageRequest(BaseModel):
    to: str
    message: str
