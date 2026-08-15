#!/bin/bash
# Abre o app com duplo-clique no Finder.
#
# Este é o caminho de abertura no macOS. O .app montado à mão não serve:
# a partir do macOS 26 o LaunchServices recusa bundle sem assinatura válida
# (erro -10669), e assinar ad-hoc depende do codesign, que nem sempre está
# saudável na máquina. O .command passa pelo Terminal e não tem esse problema.
cd "$(dirname "$0")"

if [ ! -x venv/bin/python ]; then
  echo "Ambiente não encontrado. Rode primeiro:  ./instalar.sh"
  echo "(feche esta janela quando terminar de ler)"
  exit 1
fi

# bin/ vem primeiro: é onde mora o ffmpeg estático quando a máquina não tem um.
export PATH="$(pwd)/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"
exec venv/bin/python app.py
