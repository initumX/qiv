#!/bin/bash

# Script to integrate qiv.AppImage on DE
set -e

APP_NAME="qiv"
APP_IMAGE_NAME="${APP_NAME}.AppImage"
CURRENT_DIR="$(pwd)"
APPIMAGE_PATH="$CURRENT_DIR/$APP_IMAGE_NAME"
INSTALL_DIR="$HOME/.local/bin"
DESKTOP_DIR="$HOME/.local/share/applications"
DESKTOP_FILE_NAME="${APP_NAME}.desktop"
DESKTOP_FILE_PATH="$DESKTOP_DIR/$DESKTOP_FILE_NAME"
UNINSTALL_SCRIPT_NAME="uninstall_${APP_NAME}.sh"

# Check if AppImage exists
echo "Checking for $APPIMAGE_PATH..."
if [[ ! -f "$APPIMAGE_PATH" ]]; then
  echo "❌ Error: $APPIMAGE_PATH not found in current directory."
  exit 1
fi

# Copy AppImage
echo "Copying $APP_IMAGE_NAME to $INSTALL_DIR/..."
mkdir -p "$INSTALL_DIR"
cp "$APPIMAGE_PATH" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/$APP_IMAGE_NAME"

# Create .desktop file
echo "Creating .desktop file at $DESKTOP_FILE_PATH..."
mkdir -p "$DESKTOP_DIR"
cat > "$DESKTOP_FILE_PATH" << EOF
[Desktop Entry]
Name=Qt Image Viewer
Exec=$INSTALL_DIR/$APP_IMAGE_NAME %f
Type=Application
Categories=Graphics;Viewer;
MimeType=image/jpeg;image/png;image/webp;image/gif;image/bmp;image/tiff;
Terminal=false
Comment=A lightweight and fast image viewer
Icon=application-x-executable
StartupNotify=false
EOF

# Update database
echo "Updating application database..."
update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true

# Set MIME associations
echo "Setting MIME type associations for images..."
xdg-mime default "$DESKTOP_FILE_NAME" image/jpeg
xdg-mime default "$DESKTOP_FILE_NAME" image/png
xdg-mime default "$DESKTOP_FILE_NAME" image/webp

# Generate uninstall script
UNINSTALL_SCRIPT_PATH="$(pwd)/$UNINSTALL_SCRIPT_NAME"
echo "Generating uninstall script at $UNINSTALL_SCRIPT_PATH..."
cat > "$UNINSTALL_SCRIPT_PATH" << EOF_UNINSTALL
#!/bin/bash
set -e

echo "Removing $APP_NAME..."

if [[ -f "\$HOME/.local/bin/$APP_IMAGE_NAME" ]]; then
  echo "Removing \$HOME/.local/bin/$APP_IMAGE_NAME"
  rm "\$HOME/.local/bin/$APP_IMAGE_NAME"
fi

if [[ -f "$DESKTOP_FILE_PATH" ]]; then
  echo "Removing $DESKTOP_FILE_PATH"
  rm "$DESKTOP_FILE_PATH"
fi

echo "Updating application database..."
update-desktop-database "\$HOME/.local/share/applications" 2>/dev/null || true

echo "$APP_NAME uninstalled."
EOF_UNINSTALL

chmod +x "$UNINSTALL_SCRIPT_PATH"

echo "  $APP_NAME successfully installed."
echo "   Application available in menu and opens images by default."
echo "   Uninstall with: $(pwd)/$UNINSTALL_SCRIPT_NAME"
