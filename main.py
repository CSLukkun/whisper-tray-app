#!/usr/bin/env python3
"""WhisperTray — 本地 Whisper 语音识别托盘工具入口。"""

from __future__ import annotations

import logging
import sys
from datetime import datetime
from pathlib import Path


def _setup_logging() -> Path:
    # 延迟导入 config，保证日志目录可用
    from config import get_logs_dir

    log_dir = get_logs_dir()
    log_file = log_dir / f"whisper_tray_{datetime.now().strftime('%Y%m%d')}.log"

    root = logging.getLogger()
    root.setLevel(logging.INFO)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    # console=False (frozen windowed exe) 时 stdout 可能为 None，仅写文件日志
    if sys.stdout is not None:
        sh = logging.StreamHandler(sys.stdout)
        sh.setLevel(logging.INFO)
        sh.setFormatter(fmt)
        root.addHandler(sh)

    logging.info("日志文件: %s", log_file)
    return log_file


def _check_deps() -> list[str]:
    """返回缺失/不可用依赖的提示列表。"""
    missing: list[str] = []
    import platform as _platform

    if _platform.system() == "Darwin":
        sd_tip = (
            "pip install sounddevice；若失败请先: brew install portaudio"
        )
    elif _platform.system() == "Windows":
        sd_tip = "pip install sounddevice（Windows 轮子一般自带 PortAudio）"
    else:
        sd_tip = (
            "pip install sounddevice；系统需 PortAudio "
            "（如 apt install libportaudio2 / dnf install portaudio）"
        )

    checks = (
        ("numpy", "pip install numpy"),
        ("PIL", "pip install Pillow"),
        ("pystray", "pip install pystray"),
        ("sounddevice", sd_tip),
        ("faster_whisper", "pip install faster-whisper"),
    )
    for mod, tip in checks:
        try:
            __import__(mod)
        except ImportError:
            missing.append(f"{mod} ({tip})")
        except OSError as e:
            # 例如 Linux 缺少 libportaudio 时 sounddevice 抛 OSError
            missing.append(f"{mod} [加载失败: {e}] ({tip})")
        except Exception as e:
            missing.append(f"{mod} [异常: {e}] ({tip})")
    return missing


def main() -> int:
    # Windows 控制台 UTF-8，减少中文乱码
    if sys.platform == "win32":
        try:
            if sys.stdout is not None and hasattr(sys.stdout, "reconfigure"):
                sys.stdout.reconfigure(encoding="utf-8")
            if sys.stderr is not None and hasattr(sys.stderr, "reconfigure"):
                sys.stderr.reconfigure(encoding="utf-8")
        except Exception:
            pass

    _setup_logging()
    log = logging.getLogger("main")

    log.info("Python %s | 平台 %s", sys.version.split()[0], sys.platform)
    log.info("工作目录: %s", Path.cwd())

    missing = _check_deps()
    if missing:
        log.error("缺少或不可用的依赖: %s", ", ".join(missing))
        log.error("请先运行: pip install -r requirements.txt")
        print("缺少依赖，请执行: pip install -r requirements.txt", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        return 1

    # pyperclip / plyer 为软依赖
    try:
        import pyperclip  # noqa: F401
    except ImportError:
        log.warning("未安装 pyperclip，将尝试系统剪贴板命令")

    try:
        from tray_app import TrayApp

        app = TrayApp()
        app.run()
        return 0
    except KeyboardInterrupt:
        log.info("用户中断")
        return 0
    except Exception:
        log.exception("应用异常退出")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
