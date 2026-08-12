#!/usr/bin/env bash
# Monta o Transcrição.app na Mesa (macOS).
# Chamado pelo instalar.sh, mas pode ser rodado sozinho para recriar o atalho.
#
# Não gera o ícone: o AppIcon.icns já vem versionado. Gerar exigiria Pillow
# instalado na máquina de quem instala, e ícone é trabalho de build, não de
# instalação.
set -euo pipefail

PROJETO="$(cd "$(dirname "$0")" && pwd)"
NOME="Transcrição"
APP="$HOME/Desktop/$NOME.app"

if [ ! -x "$PROJETO/venv/bin/python" ]; then
  echo "✗ Ambiente não encontrado. Rode ./instalar.sh primeiro."
  exit 1
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"

# Launcher com caminho absoluto do venv desta máquina — é o que permite
# clicar no ícone sem abrir Terminal.
cat > "$APP/Contents/MacOS/$NOME" <<LAUNCHER
#!/bin/bash
# bin/ primeiro: é onde fica o ffmpeg estático em máquina sem Homebrew.
export PATH="$PROJETO/bin:/opt/homebrew/bin:/usr/local/bin:\$PATH"
exec "$PROJETO/venv/bin/python" "$PROJETO/app.py"
LAUNCHER
chmod +x "$APP/Contents/MacOS/$NOME"

cat > "$APP/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key><string>$NOME</string>
  <key>CFBundleDisplayName</key><string>$NOME</string>
  <key>CFBundleIdentifier</key><string>br.pltca.transcricao</string>
  <key>CFBundleVersion</key><string>1.0</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleExecutable</key><string>$NOME</string>
  <key>CFBundleIconFile</key><string>AppIcon</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSMicrophoneUsageDescription</key>
  <string>Para gravar áudio e transcrever.</string>
  <key>LSUIElement</key><false/>
</dict>
</plist>
PLIST

cp "$PROJETO/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"

touch "$APP"
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister \
  -f "$APP" 2>/dev/null || true

echo "✓ Atalho criado na Mesa: $NOME.app"
