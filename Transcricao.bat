@echo off
REM Abre o app no Windows. Clique duas vezes neste arquivo.
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
    echo Ambiente nao encontrado. Rode primeiro o instalador:
    echo   powershell -ExecutionPolicy Bypass -File .\instalar.ps1
    pause
    exit /b 1
)

REM pythonw abre sem janela preta de console atras do app
start "" "venv\Scripts\pythonw.exe" app.py
