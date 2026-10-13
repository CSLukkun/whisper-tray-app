#!/usr/bin/env bash
# WhisperTray — 将 dist/WhisperTray.app 打成可分发的 .dmg（仅 macOS；依赖 hdiutil）
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[错误] 请在 macOS 上运行本脚本（需要 hdiutil）。"
  echo "Linux 本机无法生成真实 .dmg；请在 Mac 上执行，或依赖 GitHub Actions macos runner。"
  exit 1
fi

VERSION="$(tr -d '[:space:]' < VERSION)"
ARCH="$(uname -m)"
case "${ARCH}" in
  arm64|aarch64) ARCH_TAG="arm64" ;;
  x86_64|amd64)  ARCH_TAG="x86_64" ;;
  *)             ARCH_TAG="${ARCH}" ;;
esac

APP_PATH="${1:-dist/WhisperTray.app}"
if [[ ! -d "${APP_PATH}" ]]; then
  echo "[错误] 未找到 ${APP_PATH}"
  echo "请先运行 ./build_macos.sh 或 pyinstaller whisper_tray_macos.spec"
  exit 1
fi

mkdir -p dist
DMG_NAME="WhisperTray-${VERSION}-macos-${ARCH_TAG}.dmg"
DMG_PATH="dist/${DMG_NAME}"

STAGE="$(mktemp -d "${TMPDIR:-/tmp}/whispertray-dmg.XXXXXX")"
cleanup() { rm -rf "${STAGE}"; }
trap cleanup EXIT

echo "准备 DMG 暂存目录: ${STAGE}"
ditto "${APP_PATH}" "${STAGE}/WhisperTray.app"
ln -s /Applications "${STAGE}/Applications"

# 若已有同名文件先删掉，避免 hdiutil 交互提示
rm -f "${DMG_PATH}"

echo "创建压缩 DMG: ${DMG_PATH}"
hdiutil create \
  -volname "WhisperTray ${VERSION}" \
  -srcfolder "${STAGE}" \
  -ov \
  -format UDZO \
  "${DMG_PATH}"

echo
echo "完成。"
echo "  ${DMG_PATH}"
ls -lh "${DMG_PATH}"
echo
echo "安装提示（未签名）:"
echo "  1. 打开 .dmg，将 WhisperTray.app 拖到 Applications"
echo "  2. 首次启动：右键 → 打开（Gatekeeper 会拦截未签名应用）"
echo "  3. 系统设置 → 隐私与安全性 → 麦克风 → 允许 WhisperTray"
