#!/usr/bin/env bash
# WhisperTray — macOS / Linux 一键启动
set -euo pipefail
cd "$(dirname "$0")"

echo "========================================"
echo "  WhisperTray 启动脚本 (macOS/Linux)"
echo "========================================"

OS="$(uname -s)"
ARCH="$(uname -m)"
echo "系统: ${OS} / ${ARCH}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[错误] 未找到 python3，请先安装 Python 3.11+"
  if [[ "${OS}" == "Darwin" ]]; then
    echo "  建议: brew install python@3.12"
  fi
  exit 1
fi

PY_VER="$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
echo "Python: ${PY_VER} ($(command -v python3))"

# PortAudio：sounddevice 在 macOS / 多数 Linux 上依赖系统库
need_portaudio_hint=0
if [[ "${OS}" == "Darwin" ]]; then
  if command -v brew >/dev/null 2>&1; then
    if ! brew list portaudio >/dev/null 2>&1; then
      echo "[提示] 未检测到 Homebrew 的 portaudio。"
      echo "       若 pip 安装 sounddevice 失败，请执行:"
      echo "         brew install portaudio"
      need_portaudio_hint=1
    else
      echo "[OK] portaudio (Homebrew) 已安装"
    fi
  else
    echo "[提示] 未找到 Homebrew。Apple Silicon / Intel Mac 推荐先安装:"
    echo "  https://brew.sh"
    echo "  然后: brew install portaudio python@3.12"
    need_portaudio_hint=1
  fi
fi

if [[ ! -d .venv ]]; then
  echo "[1/3] 创建虚拟环境 .venv ..."
  python3 -m venv .venv
else
  echo "[1/3] 虚拟环境已存在"
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo "[2/3] 安装/更新依赖 ..."
python -m pip install --upgrade pip
if ! python -m pip install -r requirements.txt; then
  echo "[错误] 依赖安装失败。"
  if [[ "${OS}" == "Darwin" ]]; then
    echo "  常见原因: 缺少 PortAudio → brew install portaudio"
    echo "  然后重新运行: ./run.sh"
  else
    echo "  Linux 可尝试: sudo apt install libportaudio2 portaudio19-dev"
  fi
  exit 1
fi

# 快速探测 sounddevice 能否加载（缺 libportaudio 时会 OSError）
if ! python -c "import sounddevice" 2>/dev/null; then
  echo "[错误] sounddevice 无法加载（多为缺少 PortAudio）。"
  if [[ "${OS}" == "Darwin" ]]; then
    echo "  请执行: brew install portaudio"
    echo "  然后:   source .venv/bin/activate && pip install --force-reinstall sounddevice"
  fi
  exit 1
fi

echo "[3/3] 启动 WhisperTray ..."
echo "提示: 首次运行会下载 Whisper 模型（small 约 244–500MB）"
if [[ "${OS}" == "Darwin" ]]; then
  echo "macOS: 首次录音时请在「系统设置 → 隐私与安全性 → 麦克风」中允许终端/Python。"
  echo "菜单栏图标在屏幕右上角；右键（或 Control+点击）打开菜单。"
fi
echo

exec python main.py
