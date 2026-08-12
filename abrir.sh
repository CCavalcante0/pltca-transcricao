#!/usr/bin/env bash
# Abre o app. Caminho relativo ao próprio script — funciona em qualquer pasta.
cd "$(dirname "$0")"

if [ ! -x venv/bin/python ]; then
  echo "Ambiente não encontrado. Rode primeiro:  ./instalar.sh"
  exit 1
fi

exec venv/bin/python app.py
