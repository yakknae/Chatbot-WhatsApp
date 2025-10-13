#  Asistente virtual de supermercado

Asistente virtual inteligente que permite a los clientes consultar productos, armar pedidos y recibir asistencia vía WhatsApp, usando IA local (Ollama) y base de datos MySQL.

---

##  Requisitos

- **Python 3.10+**
- **MySQL 8.0+** (o MariaDB)
- **Ollama** (con modelo como `gemma3:latest`)
- **Ngrok** (para exponer el servidor local)
- **Cuenta de Twilio** (con WhatsApp Sandbox activado)

---

##  Instalación

### 1. Clonar el repositorio
```bash
git clone https://github.com/tu-usuario/Chatbot-WhatsApp.git
cd Chatbot-WhatsApp
```

## Instructivo para hacer andar el Chatbot-Ollama

Opcion 1:
Ejecutar el script .bat
> start.bat
- Este script instala dependencias, inicia el servidor FastAPI en el puerto 8000, lanza Ngrok automáticamente y levanta el servicio de Ollama para que la IA esté disponible.

Opción 2:

## Instala las dependencias:
> pip install -r requirements.txt

## Levanta el servidor FastAPI:
> uvicorn app.main:app --reload --port 8000

## Levanta el servidor con Ngrok (en un cmd):
> ngrok http 8000
- "Copia la URL pública que Ngrok genera (ej: https://abc123.ngrok.io)."

## Configura Twilio:
Ve a Twilio Console > WhatsApp > Sandbox
Escanea el QR para unirte al sandbox
Envía el mensaje de activación que te indique Twilio (ej: join explain-neighbor)
Configura el webhook con tu URL de Ngrok:
"https://abc123.ngrok.io/webhook"
- "Importante: Asegúrate de haber configurado tu archivo .env y tu base de datos antes de iniciar." 

## Enviroments credentials
```
Database credentials
> MYSQL_HOST=""
> MYSQL_USER=""
> MYSQL_PASSWORD=""
> MYSQL_DATABASE=""
> MYSQL_PORT=""

Twilio credentials
> From=
> Body=
> TWILIO_ACCOUNT_SID=
> TWILIO_AUTH_TOKEN=
> TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
> ACCESS_TOKEN=
```

## Project Structure
```
Chatbot-WhatsApp/
├── app/
│   ├── __init__.py
│   ├── endpoints/
│   │   └── endpoints.py       
│   ├── crud.py                
│   ├── database.py            
│   ├── main.py                
│   ├── schemas.py            
│   └── twilio_client.py       
├── prompts/
│   ├── prompt_input.txt      
│   └── prompt_output.txt    
├── conversaciones/           
├── script/
├── test/
├── .env                     
├── .gitattributes
├── .gitignore                         
├── README.md
├── requirements.txt          
└── start.bat                               
```
