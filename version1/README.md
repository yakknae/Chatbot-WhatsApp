# Asistente virtual de supermercado

Asistente virtual inteligente que permite a los clientes consultar productos, armar pedidos y recibir asistencia vía WhatsApp, usando IA local (Ollama) y base de datos MySQL.

---

## Requisitos

- **Python 3.10+**
- **Node.js 18+** (para `whatsapp-web.js`)
- **MySQL 8.0+** (o MariaDB)
- **Ollama** (con un modelo como `gemma3:latest`, `llama3`, etc.)
- **Google Chrome** (requerido por Puppeteer en `whatsapp-web.js`)

---

## Instalación

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

## Enviroments credentials

```
Database credentials
> MYSQL_HOST=""
> MYSQL_USER=""
> MYSQL_PASSWORD=""
> MYSQL_DATABASE=""
> MYSQL_PORT=""


## Project Structure

```

version1/
├── app/
│ ├── **init**.py
│ ├── endpoints/
│ │ └── endpoints.py
│ ├── crud.py
│ ├── database.py
│ ├── main.py
│ ├── schemas.py
│ └── twilio_client.py
├── prompts/
│ ├── prompt_input.txt
│ └── prompt_output.txt
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

```
