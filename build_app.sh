#!/usr/bin/env bash
# Monta o Transcrição.app na Mesa (macOS): ícone de verdade, duplo-clique,
# sem janela de Terminal — como qualquer app do Mac.
#
# Por que via osacompile e não um bundle montado à mão:
#
# A partir do macOS 26 o LaunchServices recusa abrir bundle sem assinatura
# válida — o duplo-clique falha com -10669 e nada acontece na tela, que é o
# pior tipo de defeito: parece que o app inteiro está quebrado. Um bundle
# escrito com mkdir + cat nasce sem assinatura nenhuma, e assinar depois com
# `codesign -s -` não é confiável na máquina de quem instala (num Mac aqui o
# codesign morreu com SIGBUS tentando assinar um executável de shell script).
#
# O osacompile resolve isso de graça: o executável do bundle é o `applet` da
# própria Apple, um Mach-O que já sai assinado ad-hoc pela ferramenta. O que
# resta é trocar o ícone e reassinar — e reassinar um Mach-O funciona onde
# assinar um shell script não funcionava.
set -euo pipefail

PROJETO="$(cd "$(dirname "$0")" && pwd)"
NOME="Transcrição"
APP="$HOME/Desktop/$NOME.app"

if [ ! -x "$PROJETO/venv/bin/python" ]; then
  echo "✗ Ambiente não encontrado. Rode ./instalar.sh primeiro."
  exit 1
fi

# `do shell script` espera o comando terminar; o app roda até a pessoa fechar.
# Daí o nohup em segundo plano: o applet dispara e sai, sem prender o Finder.
#
# O pgrep evita a segunda instância — dois cliques no ícone abririam duas
# janelas mexendo no mesmo banco.
#
# O `[a]` não é enfeite. O pgrep -f lê a linha de comando de todo processo,
# inclusive a do `sh -c` que está rodando este próprio if — que contém o
# padrão procurado. Sem o colchete o guarda encontra a si mesmo, conclui que
# o app já está aberto e nunca abre nada: o ícone vira enfeite. Com ele, o
# texto literal do wrapper ("[a]pp.py") deixa de casar com a regex, que
# continua casando com o processo python de verdade ("app.py").
LANCAR="if ! /usr/bin/pgrep -f 'pltca-transcricao/[a]pp.py' > /dev/null 2>&1; then cd '$PROJETO' && export PATH=\\\"$PROJETO/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH\\\" && nohup '$PROJETO/venv/bin/python' '$PROJETO/app.py' > /dev/null 2>&1 & fi"

rm -rf "$APP"
osacompile -o "$APP" -e "do shell script \"$LANCAR\"" 2>/dev/null

# Ícone: o osacompile deixa um applet.icns em Resources e o Info.plist já
# aponta pra ele. Trocar o arquivo no lugar evita mexer no plist.
cp "$PROJETO/AppIcon.icns" "$APP/Contents/Resources/applet.icns"

/usr/libexec/PlistBuddy -c "Set :CFBundleName $NOME" "$APP/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :CFBundleDisplayName string $NOME" "$APP/Contents/Info.plist" 2>/dev/null || true
/usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string Para gravar áudio e transcrever." "$APP/Contents/Info.plist" 2>/dev/null || true

# Trocar ícone e plist quebra o selo da assinatura que veio do osacompile;
# sem reassinar, o -10669 volta.
codesign --force --sign - "$APP" 2>/dev/null

# Faz o Finder reler o ícone em vez de mostrar o genérico do cache.
touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister \
  -f "$APP" 2>/dev/null || true

# Restos das duas tentativas anteriores de atalho.
rm -f "$HOME/Desktop/Abrir Transcrição.command"

echo "✓ Atalho criado na Mesa: $NOME.app"
