#!/usr/bin/env bash
# Abre o app. Caminho relativo ao próprio script — funciona em qualquer pasta.
cd "$(dirname "$0")"

if [ ! -x venv/bin/python ]; then
  echo "Ambiente não encontrado. Rode primeiro:  ./instalar.sh"
  exit 1
fi

# bin/ vem primeiro: é onde mora o ffmpeg estático quando a máquina não tem um.
export PATH="$(pwd)/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
exec venv/bin/python app.py
