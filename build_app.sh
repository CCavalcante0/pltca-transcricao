#!/usr/bin/env bash
# Põe o atalho de abrir na Mesa (macOS).
# Chamado pelo instalar.sh, mas pode ser rodado sozinho para recriar o atalho.
#
# Por que não é mais um .app montado à mão:
#
# A partir do macOS 26 o LaunchServices recusa abrir bundle sem assinatura
# válida — o duplo-clique falha com -10669 e nada acontece na tela, que é o
# pior tipo de defeito: parece que o app simplesmente não funciona. Assinar
# ad-hoc resolveria, mas depende do codesign estar saudável na máquina de
# quem instala, e ele nem sempre está. Pior: quando a Mesa está sincronizada
# pelo iCloud, o file provider reestampa `com.apple.FinderInfo` no bundle e
# o codesign passa a recusar assinar ("resource fork ... not allowed").
#
# O .command não passa por esse caminho: abre pelo Terminal e funciona sem
# assinatura, com ou sem iCloud. Perde-se o ícone bonito; ganha-se um atalho
# que abre.
set -euo pipefail

PROJETO="$(cd "$(dirname "$0")" && pwd)"
ALVO="$PROJETO/Abrir Transcrição.command"
ATALHO="$HOME/Desktop/Abrir Transcrição.command"

if [ ! -x "$PROJETO/venv/bin/python" ]; then
  echo "✗ Ambiente não encontrado. Rode ./instalar.sh primeiro."
  exit 1
fi

chmod +x "$ALVO"

# Restos de versões antigas: o bundle não abre, e deixá-lo na Mesa só faz a
# pessoa clicar no ícone errado.
rm -rf "$HOME/Desktop/Transcrição.app"

ln -sfn "$ALVO" "$ATALHO"

echo "✓ Atalho criado na Mesa: Abrir Transcrição.command"
