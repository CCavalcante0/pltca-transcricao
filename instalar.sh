#!/usr/bin/env bash
# Instalador do app de transcrição — macOS e Linux.
# Rode uma vez:  ./instalar.sh
#
# Numa máquina zerada, sem Homebrew e sem Python, ele resolve tudo sozinho
# e sem pedir senha: o uv baixa um Python próprio e o ffmpeg vem como
# binário estático dentro da pasta do projeto.
set -euo pipefail

cd "$(dirname "$0")"
PROJETO="$(pwd)"
BIN="$PROJETO/bin"
export PATH="$BIN:$PATH"

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

UV=""
if [ -z "$PY" ]; then
  echo "→ Python 3.10+ não encontrado. Baixando um com o uv (sem senha, sem Homebrew)…"
  UV="$(command -v uv || true)"
  [ -z "$UV" ] && [ -x "$HOME/.local/bin/uv" ] && UV="$HOME/.local/bin/uv"
  if [ -z "$UV" ]; then
    curl -LsSf https://astral.sh/uv/install.sh | sh >/dev/null 2>&1 || true
    UV="$HOME/.local/bin/uv"
  fi
  if [ ! -x "$UV" ]; then
    echo "✗ Não consegui instalar o uv. Instale o Python manualmente:"
    echo "    https://python.org/downloads"
    exit 1
  fi
  echo "✓ uv pronto"
else
  echo "✓ Python: $($PY --version)"
fi

# ── 2. ffmpeg ────────────────────────────────────────────────────────
if ! command -v ffmpeg >/dev/null 2>&1 || ! command -v ffprobe >/dev/null 2>&1; then
  if [ "$(uname)" = "Darwin" ]; then
    # Binário estático na pasta do projeto: não precisa de Homebrew nem senha.
    case "$(uname -m)" in
      arm64) SUF="9arm" ;;
      *)     SUF="80intel" ;;
    esac
    echo "→ ffmpeg não encontrado, baixando build estático ($(uname -m))…"
    mkdir -p "$BIN"
    for b in ffmpeg ffprobe; do
      curl -sSL --retry 2 -o "/tmp/$b.zip" "https://www.osxexperts.net/${b}${SUF}.zip"
      unzip -qo "/tmp/$b.zip" -d "$BIN" -x '__MACOSX/*'
      rm -f "/tmp/$b.zip"
      chmod +x "$BIN/$b"
      xattr -d com.apple.quarantine "$BIN/$b" 2>/dev/null || true
    done
  elif command -v apt >/dev/null 2>&1; then
    sudo apt update && sudo apt install -y ffmpeg
  else
    echo "✗ Instale o ffmpeg manualmente e rode de novo."
    exit 1
  fi
fi
command -v ffmpeg >/dev/null 2>&1 || { echo "✗ ffmpeg ainda indisponível."; exit 1; }
echo "✓ ffmpeg: $(ffmpeg -version | head -1 | cut -d' ' -f3)"

# ── 3. Ambiente virtual ──────────────────────────────────────────────
if [ ! -d venv ]; then
  echo "→ Criando ambiente virtual…"
  if [ -n "$PY" ]; then
    "$PY" -m venv venv
  else
    "$UV" venv --seed --python 3.12 venv
  fi
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

# ── 5. Atalho na Mesa (só macOS) ─────────────────────────────────────
ABRIR="./abrir.sh"
if [ "$(uname)" = "Darwin" ]; then
  bash "$PROJETO/build_app.sh" && ABRIR="o 'Abrir Transcrição' na sua Mesa"
fi

echo
echo "════════════════════════════════════════════"
echo "  Instalação concluída."
echo
echo "  Para abrir:  $ABRIR"
echo
echo "  Na primeira transcrição ele baixa o modelo"
echo "  do Whisper (1,5 GB). Isso acontece uma vez só."
echo "════════════════════════════════════════════"
