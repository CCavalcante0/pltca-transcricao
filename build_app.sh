#!/bin/bash
set -e

PROJECT="$(cd "$(dirname "$0")" && pwd)"
APP_NAME="Transcrição"
DESKTOP="$HOME/Desktop"
APP_OUT="$DESKTOP/$APP_NAME.app"

FRAMEWORK_PYTHON="$(ls /opt/homebrew/opt/python*/Frameworks/Python.framework/Versions/*/bin/python3 2>/dev/null | head -1)"
if [ -z "$FRAMEWORK_PYTHON" ]; then
  FRAMEWORK_PYTHON="$(ls /opt/homebrew/Cellar/python*/*/Frameworks/Python.framework/Versions/*/MacOS/Python 2>/dev/null | head -1)"
fi
if [ -z "$FRAMEWORK_PYTHON" ]; then
  echo "Erro: framework Python não encontrado. Instale via Homebrew."
  exit 1
fi
echo "▶ Usando Python: $FRAMEWORK_PYTHON"

echo "▶ Gerando ícone..."

PROJECT="$PROJECT" "$PROJECT/venv/bin/python3" - <<'PYEOF'
from PIL import Image, ImageDraw
import os, sys

size = 1024
img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# Fundo azul iOS com cantos arredondados
draw.rounded_rectangle([(0, 0), (size, size)], radius=220, fill=(0, 122, 255, 255))

# Waveform branca centralizada
bars    = [0.22, 0.42, 0.62, 0.80, 0.95, 1.00, 0.88, 0.70, 0.52, 0.38, 0.60, 0.45, 0.25]
bw      = 46
gap     = 22
total_w = len(bars) * bw + (len(bars) - 1) * gap
sx      = (size - total_w) // 2
cy      = size // 2

for i, h in enumerate(bars):
    bh = int(360 * h)
    x  = sx + i * (bw + gap)
    draw.rounded_rectangle(
        [(x, cy - bh // 2), (x + bw, cy + bh // 2)],
        radius=bw // 2,
        fill=(255, 255, 255, 230),
    )

out = os.path.join(os.environ["PROJECT"], "icon_1024.png")
img.save(out)
print(f"  ícone salvo: {out}")
PYEOF

echo "▶ Convertendo para .icns..."
ICONSET="$PROJECT/AppIcon.iconset"
rm -rf "$ICONSET" && mkdir "$ICONSET"

for s in 16 32 128 256 512; do
    sips -z $s $s "$PROJECT/icon_1024.png" --out "$ICONSET/icon_${s}x${s}.png"        > /dev/null
done
sips -z 32   32   "$PROJECT/icon_1024.png" --out "$ICONSET/icon_16x16@2x.png"         > /dev/null
sips -z 64   64   "$PROJECT/icon_1024.png" --out "$ICONSET/icon_32x32@2x.png"         > /dev/null
sips -z 256  256  "$PROJECT/icon_1024.png" --out "$ICONSET/icon_128x128@2x.png"       > /dev/null
sips -z 512  512  "$PROJECT/icon_1024.png" --out "$ICONSET/icon_256x256@2x.png"       > /dev/null
sips -z 1024 1024 "$PROJECT/icon_1024.png" --out "$ICONSET/icon_512x512@2x.png"       > /dev/null
iconutil -c icns "$ICONSET" -o "$PROJECT/AppIcon.icns"
rm -rf "$ICONSET"
echo "  AppIcon.icns criado"

echo "▶ Montando .app..."
rm -rf "$APP_OUT"
mkdir -p "$APP_OUT/Contents/MacOS"
mkdir -p "$APP_OUT/Contents/Resources"

# Launcher shell script (usa framework Python para GUI correta no macOS)
VENV_SITE="$PROJECT/venv/lib/$(ls "$PROJECT/venv/lib/" | head -1)/site-packages"

cat > "$APP_OUT/Contents/MacOS/$APP_NAME" <<LAUNCHER
#!/bin/bash
export PYTHONPATH="$VENV_SITE"
export PATH="/opt/homebrew/opt/openjdk/bin:/opt/homebrew/bin:\$PATH"
exec "$FRAMEWORK_PYTHON" "$PROJECT/app.py"
LAUNCHER

chmod +x "$APP_OUT/Contents/MacOS/$APP_NAME"

# Info.plist
cat > "$APP_OUT/Contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>
  <string>$APP_NAME</string>
  <key>CFBundleDisplayName</key>
  <string>$APP_NAME</string>
  <key>CFBundleIdentifier</key>
  <string>br.local.transcricao</string>
  <key>CFBundleVersion</key>
  <string>1.0</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleExecutable</key>
  <string>$APP_NAME</string>
  <key>CFBundleIconFile</key>
  <string>AppIcon</string>
  <key>NSHighResolutionCapable</key>
  <true/>
  <key>LSUIElement</key>
  <false/>
</dict>
</plist>
PLIST

echo "▶ Aplicando ícone..."
cp "$PROJECT/AppIcon.icns" "$APP_OUT/Contents/Resources/AppIcon.icns"

# Força o macOS a atualizar o cache de ícones
touch "$APP_OUT"
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister \
  -f "$APP_OUT" 2>/dev/null || true

echo ""
echo "✓ Pronto! O app está na sua Mesa:"
echo "  $APP_OUT"
echo ""
echo "  Se o ícone ainda aparecer genérico, arraste o app para o Dock"
echo "  e abra uma vez — o macOS atualiza o cache automaticamente."
