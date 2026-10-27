#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# The YiJing (I Ching) — Navigating Change — Flatpak Build Script
# Script version 1.0.2 — Wednesday 28 October 2026
# Run from build directory:
#   ./build.sh            build the .flatpak bundle only (default — repo-safe)
#   ./build.sh --install  build, then install to the user Flatpak
#   ./build.sh --run      build, install, then launch (the old dev loop)
# Version is read automatically from yijing_main.py — do not edit here.
# ══════════════════════════════════════════════════════════════════════════════

set -e

# ── Options ───────────────────────────────────────────────────────────────────
INSTALL=0
RUN=0
for arg in "$@"; do
  case "$arg" in
    --install) INSTALL=1 ;;
    --run)     INSTALL=1; RUN=1 ;;
    -h|--help)
      echo "Usage: ./build.sh [--install] [--run]"
      echo "  (no flag)   build the .flatpak bundle only"
      echo "  --install   build, then install to the user Flatpak"
      echo "  --run       build, install, then launch"
      exit 0 ;;
    *) echo "Unknown option: $arg"; echo "Usage: ./build.sh [--install] [--run]"; exit 1 ;;
  esac
done

# ── Read identity from source ─────────────────────────────────────────────────
VERSION=$(grep 'APP_VER' yijing_main.py | head -1 | grep -oP '"\K[^"]+')
APP_ID=$(grep 'APP_ID' yijing_main.py | head -1 | grep -oP '"\K[^"]+')
BUILD_DATE=$(date +%Y-%m-%d)
BUNDLE="YiJingNavigatingChange-${VERSION}-x86_64.flatpak"
WORKDIR="yijing_fp"
REPO="yijing_repo"

echo "Building version ${VERSION} (${APP_ID})"

# ── Step 1: PyInstaller ───────────────────────────────────────────────────────
pyinstaller \
  --onefile \
  --name "YiJingNavigatingChange" \
  --add-data "book:book" \
  --add-data "content:content" \
  --add-data "opening_image.png:." \
  --add-data "ukai_yijing.ttf:." \
  --add-data "aoyagi_yijing.ttf:." \
  --add-data "coin_images.py:." \
  --add-data "yarrow_animation.py:." \
  --add-data "icon_64.png:." \
  --add-data "icon_128.png:." \
  --add-data "icon_256.png:." \
  --hidden-import PySide6.QtPrintSupport \
  --hidden-import PySide6.QtWebEngineWidgets \
  --hidden-import PySide6.QtWebEngineCore \
  --hidden-import PySide6.QtWebChannel \
  --collect-all PySide6 \
  yijing_main.py

# ── Step 2: Flatpak structure ─────────────────────────────────────────────────
rm -rf "$WORKDIR" "$REPO"

# Desktop file, icons and metainfo live in files/share (where the AppStream
# compose step reads them) and are copied to export/share (what the desktop sees).
SHARE="$WORKDIR/files/share"
mkdir -p "$WORKDIR/files/bin" \
         "$SHARE/applications" \
         "$SHARE/icons/hicolor/256x256/apps" \
         "$SHARE/icons/hicolor/128x128/apps" \
         "$SHARE/icons/hicolor/64x64/apps" \
         "$SHARE/metainfo"

cp dist/YiJingNavigatingChange "$WORKDIR/files/bin/"
chmod +x "$WORKDIR/files/bin/YiJingNavigatingChange"

cp icon_256.png "$SHARE/icons/hicolor/256x256/apps/${APP_ID}.png"
cp icon_128.png "$SHARE/icons/hicolor/128x128/apps/${APP_ID}.png"
cp icon_64.png  "$SHARE/icons/hicolor/64x64/apps/${APP_ID}.png"

cat > "$SHARE/applications/${APP_ID}.desktop" << DESK
[Desktop Entry]
Type=Application
Name=The YiJing (I Ching) — Navigating Change
GenericName=YiJing Oracle
Comment=Cast hexagrams and consult the Book of Changes
Exec=YiJingNavigatingChange
Icon=${APP_ID}
Categories=Education;Literature;
StartupWMClass=YiJingNavigatingChange
Terminal=false
DESK

cat > "$SHARE/metainfo/${APP_ID}.metainfo.xml" << META
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>${APP_ID}</id>
  <name>The YiJing (I Ching) — Navigating Change</name>
  <summary>Cast hexagrams and consult the Book of Changes</summary>
  <launchable type="desktop-id">${APP_ID}.desktop</launchable>
  <developer id="io.archerprojects"><name>archerprojects</name></developer>
  <url type="homepage">https://github.com/archerprojects/The-Yi-Jing---Navigating-Change</url>
  <content_rating type="oars-1.1"/>
  <metadata_license>MIT</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <description>
    <p>Cast hexagrams by coin or yarrow and read across five sources —
    Wilhelm, Legge, Hatcher, the Chinese text, and the Ten Wings — with a
    reading journal, study wheel, commentaries, and history. Python/PySide6.</p>
  </description>
  <releases><release version="${VERSION}" date="${BUILD_DATE}"/></releases>
</component>
META

# AppStream catalogue (what software centres read) into files/share/app-info
appstreamcli compose --prefix=/ --origin="${APP_ID}" --components="${APP_ID}" \
    --result-root="$WORKDIR/files" \
    --data-dir="$SHARE/app-info/xmls" \
    --icons-dir="$SHARE/app-info/icons/flatpak" \
    "$WORKDIR/files"

mkdir -p "$WORKDIR/export/share"
cp -r "$SHARE/applications" "$SHARE/icons" "$SHARE/metainfo" "$WORKDIR/export/share/"

cat > "$WORKDIR/metadata" << 'META'
[Application]
name=io.archerprojects.YiJingNavigatingChange
runtime=org.freedesktop.Platform/x86_64/25.08
sdk=org.freedesktop.Sdk/x86_64/25.08
command=YiJingNavigatingChange

[Context]
shared=ipc;
sockets=wayland;fallback-x11;
devices=dri;
filesystems=home;
META

# ── Step 3: Export and bundle ─────────────────────────────────────────────────
flatpak build-export --arch=x86_64 "$REPO" "$WORKDIR" stable
flatpak build-update-repo "$REPO"

flatpak build-bundle --arch=x86_64 \
    --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo \
    "$REPO" \
    "${BUNDLE}" \
    "$APP_ID" stable

echo "Bundle: ${BUNDLE}"

# ── Step 4: Install and run (only with --install / --run) ─────────────────────
if [ "$INSTALL" -eq 1 ]; then
  flatpak uninstall --user --noninteractive "$APP_ID" 2>/dev/null || true
  flatpak install --user --noninteractive "${BUNDLE}"
  echo "Installed ${APP_ID}"
  if [ "$RUN" -eq 1 ]; then
    flatpak run "$APP_ID"
  fi
fi
