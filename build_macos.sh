#!/usr/bin/env bash
# WhisperTray — 在 macOS 本机打包 .app 与 .dmg（无法在 Linux 上交叉编译）
set -euo pipefail
cd "$(dirname "$0")"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "[错误] 请在 macOS 上运行本脚本。"
  echo "本 Linux/CI 构建机无法产出可用的 macOS .app（无法交叉签名/链接 Cocoa）。"
  echo "请在 Mac 上克隆仓库后执行: ./build_macos.sh"
  exit 1
fi

echo "========================================"
echo "  WhisperTray macOS 打包"
echo "  arch=$(uname -m)  python=$(command -v python3)"
echo "========================================"

if command -v brew >/dev/null 2>&1; then
  brew list portaudio >/dev/null 2>&1 || brew install portaudio
else
  echo "[警告] 未找到 Homebrew，若 sounddevice 链接失败请先安装 portaudio"
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo "执行 PyInstaller (whisper_tray_macos.spec) ..."
pyinstaller whisper_tray_macos.spec

echo
echo "打包 .dmg ..."
./package_macos_dmg.sh dist/WhisperTray.app

VERSION="$(tr -d '[:space:]' < VERSION)"
ARCH="$(uname -m)"
case "${ARCH}" in
  arm64|aarch64) ARCH_TAG="arm64" ;;
  x86_64|amd64)  ARCH_TAG="x86_64" ;;
  *)             ARCH_TAG="${ARCH}" ;;
esac

echo
echo "完成。输出:"
echo "  dist/WhisperTray.app"
echo "  dist/WhisperTray-${VERSION}-macos-${ARCH_TAG}.dmg"
echo
echo "限制:"
echo "  - 未做 Apple Developer 签名/公证；首次打开可能需「右键 → 打开」"
echo "  - 麦克风权限需在「系统设置 → 隐私与安全性 → 麦克风」中授予 WhisperTray"
echo "  - 模型权重不打进包内，首次运行仍会下载到 Hugging Face 缓存"
echo "  - .dmg 仅可在 macOS 上用 hdiutil 生成（本脚本与 GitHub Actions macos runner）"
