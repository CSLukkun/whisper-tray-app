"""剪贴板工具。"""

from __future__ import annotations

import logging
import os
import platform
import subprocess

logger = logging.getLogger(__name__)


def copy_to_clipboard(text: str) -> bool:
    """将文本复制到系统剪贴板。成功返回 True。"""
    if text is None:
        text = ""
    text = str(text)

    # 优先 pyperclip
    try:
        import pyperclip

        pyperclip.copy(text)
        logger.info("已复制到剪贴板（pyperclip），长度=%d", len(text))
        return True
    except Exception as e:
        logger.warning("pyperclip 失败: %s，尝试系统命令", e)

    system = platform.system()
    try:
        if system == "Windows":
            # PowerShell Set-Clipboard 对 Unicode 更友好
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value $input"],
                input=text.encode("utf-16le"),
                check=False,
                capture_output=True,
            )
            if proc.returncode == 0:
                logger.info("已复制到剪贴板（PowerShell）")
                return True
            # 回退 clip.exe（ANSI 可能有问题，但仍尝试）
            proc = subprocess.run(
                ["clip"],
                input=text.encode("utf-8", errors="replace"),
                check=False,
                capture_output=True,
            )
            if proc.returncode == 0:
                logger.info("已复制到剪贴板（clip）")
                return True
        elif system == "Darwin":
            env = os.environ.copy()
            env.setdefault("LANG", "en_US.UTF-8")
            env.setdefault("LC_ALL", "en_US.UTF-8")
            proc = subprocess.run(
                ["pbcopy"],
                input=text.encode("utf-8"),
                check=False,
                capture_output=True,
                env=env,
            )
            if proc.returncode == 0:
                logger.info("已复制到剪贴板（pbcopy），长度=%d", len(text))
                return True
        else:
            # Linux: xclip / xsel / wl-copy
            for cmd in (
                ["xclip", "-selection", "clipboard"],
                ["xsel", "--clipboard", "--input"],
                ["wl-copy"],
            ):
                try:
                    proc = subprocess.run(
                        cmd,
                        input=text.encode("utf-8"),
                        check=False,
                        capture_output=True,
                    )
                    if proc.returncode == 0:
                        logger.info("已复制到剪贴板（%s）", cmd[0])
                        return True
                except FileNotFoundError:
                    continue
    except Exception as e:
        logger.error("剪贴板复制失败: %s", e)

    logger.error("无法复制到剪贴板")
    return False
