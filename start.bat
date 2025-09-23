@echo off

:: Cambiando al directorio del script
cd /d "%~dp0"

:: Instalar dependencias
echo Instalando dependencias...
pip install -r requirements.txt


:: Verificar instalacion de Uvicorn
where uvicorn >nul 2>&1
if %errorlevel% neq 0 (
    echo error:  uvicorn no está instalado. Intenta instalarlo con: pip install uvicorn
    pause
    exit /b 1
) 

start "Ollama Backend" "%LOCALAPPDATA%\Programs\Ollama\ollama.exe" serve

:: Esperar unos segundos a que Ollama arranque
timeout /t 5 >nul

:: Iniciar Ngrok
start "Ngrok" cmd /k "Ngrok http 8000"
timeout /t 3 >nul

:: Iniciar aplicacion 
uvicorn app.main:app --reload --port 8000
pause


rem start "C:\Users\valen\AppData\Local\Programs\Ollama\ollama app.exe'
:: Cambiar C:\Users\valen por %appdata%

