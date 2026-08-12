@echo off
REM Abre o app no Windows. Clique duas vezes neste arquivo.
cd /d "%~dp0"

if not exist "venv\Scripts\pythonw.exe" (
    echo Ambiente nao encontrado. Rode primeiro o instalador:
    echo   powershell -ExecutionPolicy Bypass -File .\instalar.ps1
    pause
    exit /b 1
)

REM bin\ primeiro, caso o ffmpeg tenha sido baixado para a pasta do projeto
set "PATH=%~dp0bin;%PATH%"

REM pythonw abre sem janela preta de console atras do app
start "" "venv\Scripts\pythonw.exe" app.py
