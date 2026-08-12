# Instalador do app de transcrição — Windows.
# Rode uma vez, no PowerShell, dentro da pasta do projeto:
#   powershell -ExecutionPolicy Bypass -File .\instalar.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "════════════════════════════════════════════"
Write-Host "  Transcricao PLTCA_ - instalacao"
Write-Host "════════════════════════════════════════════"
Write-Host ""

# ── 1. Python ────────────────────────────────────────────────────────
$py = $null
foreach ($c in @("python", "python3", "py")) {
    try {
        $v = & $c -c "import sys; print(sys.version_info[0]*100+sys.version_info[1])" 2>$null
        if ($LASTEXITCODE -eq 0 -and [int]$v -ge 310) { $py = $c; break }
    } catch {}
}
if (-not $py) {
    Write-Host "X Python 3.10 ou mais novo nao encontrado." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Instale pela Microsoft Store (procure 'Python 3.12')"
    Write-Host "  ou em https://python.org/downloads"
    Write-Host "  IMPORTANTE: marque 'Add Python to PATH' na instalacao."
    exit 1
}
Write-Host "OK Python: $(& $py --version)"

# ── 2. ffmpeg ────────────────────────────────────────────────────────
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Host "-> ffmpeg nao encontrado, tentando instalar via winget..."
    try {
        winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
        Write-Host ""
        Write-Host "!! FECHE E REABRA o PowerShell para o ffmpeg entrar no PATH," -ForegroundColor Yellow
        Write-Host "   depois rode este instalador de novo." -ForegroundColor Yellow
        exit 0
    } catch {
        Write-Host "X Instale o ffmpeg manualmente: https://www.gyan.dev/ffmpeg/builds/" -ForegroundColor Red
        Write-Host "  Extraia e adicione a pasta bin ao PATH do Windows."
        exit 1
    }
}
Write-Host "OK ffmpeg encontrado"

# ── 3. Ambiente virtual ──────────────────────────────────────────────
if (-not (Test-Path "venv")) {
    Write-Host "-> Criando ambiente virtual..."
    & $py -m venv venv
}
Write-Host "OK Ambiente virtual pronto"

Write-Host "-> Instalando dependencias (demora alguns minutos na primeira vez)..."
& .\venv\Scripts\python.exe -m pip install --quiet --upgrade pip
& .\venv\Scripts\python.exe -m pip install --quiet -r requirements.txt
Write-Host "OK Dependencias instaladas"

# ── 4. Modelos de diarização (34 MB) ─────────────────────────────────
Write-Host "-> Baixando modelos de identificacao de locutor (34 MB)..."
& .\venv\Scripts\python.exe -c @"
import sys; sys.path.insert(0, '.')
from app import garantir_modelos_diarizacao, progresso_console
garantir_modelos_diarizacao(progresso_console())
"@
Write-Host "OK Modelos de locutor prontos"

Write-Host ""
Write-Host "════════════════════════════════════════════"
Write-Host "  Instalacao concluida."
Write-Host ""
Write-Host "  Para abrir: clique duas vezes em Transcricao.bat"
Write-Host ""
Write-Host "  Na primeira transcricao ele baixa o modelo"
Write-Host "  do Whisper (1,5 GB). Isso acontece uma vez so."
Write-Host "════════════════════════════════════════════"
