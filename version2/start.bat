@echo off

:: === 1. Cambiando al directorio del script ===
cd /d "%~dp0"

:: === 1.5 Crear y activar entorno virtual si no existe ===
if not exist venv (
    echo Creando entorno virtual...
    python -m venv venv
)
call venv\Scripts\activate

:: === 2. Instalar dependencias ===
echo Instalando dependencias...
pip install -r requirements.txt


:: === 3. Verificar instalacion de Uvicorn ===
where uvicorn >nul 2>&1
if %errorlevel% neq 0 (
    echo error:  uvicorn no está instalado. Intenta instalarlo con: pip install uvicorn
    pause
    exit /b 1
) 

:: === 4. Verificar Node.js ===
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Node.js no encontrado. Instálalo desde https://nodejs.org
    pause
    exit /b 1
)

:: === 5. Dependencias de Node.js ===
if not exist node_modules (
    echo Instalando dependencias de Node.js...
    npm install
) else (
    echo Dependencias de Node.js ya instaladas.
)

:: === 6. Iniciar Ollama Backend ===
start "Ollama Backend" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve
timeout /t 5 >nul

:: === 7. Iniciar WhatsApp ===
start "WhatsApp" cmd /k "node bot.js"
timeout /t 3 >nul

:: === 8. Iniciar aplicacion python ===
uvicorn app.main:app --reload --port 8000
pause



