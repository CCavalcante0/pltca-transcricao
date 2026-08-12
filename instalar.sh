#!/usr/bin/env bash
# Instalador do app de transcrição — macOS e Linux.
# Rode uma vez:  ./instalar.sh
set -euo pipefail

cd "$(dirname "$0")"
echo "════════════════════════════════════════════"
echo "  Transcrição PLTCA_ — instalação"
echo "════════════════════════════════════════════"
echo

# ── 1. Python ────────────────────────────────────────────────────────
PY=""
for cand in python3.14 python3.13 python3.12 python3.11 python3; do
  if command -v "$cand" >/dev/null 2>&1; then
    v=$("$cand" -c 'import sys; print(sys.version_info[0]*100+sys.version_info[1])' 2>/dev/null || echo 0)
    if [ "$v" -ge 310 ]; then PY="$cand"; break; fi
  fi
done

if [ -z "$PY" ]; then
  echo "✗ Python 3.10 ou mais novo não encontrado."
  echo
  echo "  macOS:  brew install python"
  echo "  Ubuntu: sudo apt install python3 python3-venv"
  exit 1
fi
echo "✓ Python: $($PY --version)"

# ── 2. ffmpeg ────────────────────────────────────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  echo "→ ffmpeg não encontrado, instalando…"
  if command -v brew >/dev/null 2>&1; then
    brew install ffmpeg
  elif command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y ffmpeg
  else
    echo "✗ Instale o ffmpeg manualmente e rode de novo."
    echo "  macOS: instale o Homebrew em https://brew.sh e depois: brew install ffmpeg"
    exit 1
  fi
fi
echo "✓ ffmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3)"

# ── 3. Ambiente virtual ──────────────────────────────────────────────
if [ ! -d venv ]; then
  echo "→ Criando ambiente virtual…"
  "$PY" -m venv venv
fi
echo "✓ Ambiente virtual pronto"

echo "→ Instalando dependências (demora alguns minutos na primeira vez)…"
./venv/bin/pip install --quiet --upgrade pip
./venv/bin/pip install --quiet -r requirements.txt
echo "✓ Dependências instaladas"

# ── 4. Modelos de diarização (34 MB) ─────────────────────────────────
echo "→ Baixando modelos de identificação de locutor (34 MB)…"
./venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from app import garantir_modelos_diarizacao, progresso_console
garantir_modelos_diarizacao(progresso_console())
"
echo "✓ Modelos de locutor prontos"

echo
echo "════════════════════════════════════════════"
echo "  Instalação concluída."
echo
echo "  Para abrir:  ./abrir.sh"
echo
echo "  Na primeira transcrição ele baixa o modelo"
echo "  do Whisper (1,5 GB). Isso acontece uma vez só."
echo "════════════════════════════════════════════"
