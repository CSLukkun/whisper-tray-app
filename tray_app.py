"""系统托盘应用：图标、菜单、录音/识别流程。"""

from __future__ import annotations

import logging
import platform
import subprocess
import sys
import threading
import time
from enum import Enum, auto
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw

from clipboard_util import copy_to_clipboard
from config import (
    AVAILABLE_LANGUAGES,
    AVAILABLE_MODELS,
    Config,
    get_data_dir,
    get_logs_dir,
    get_recordings_dir,
)
from recorder import Recorder
from transcriber import Transcriber

logger = logging.getLogger(__name__)


class AppState(Enum):
    LOADING = auto()
    IDLE = auto()
    RECORDING = auto()
    TRANSCRIBING = auto()
    DONE = auto()
    ERROR = auto()


STATE_TITLES = {
    AppState.LOADING: "加载中…",
    AppState.IDLE: "空闲 / 点击录音",
    AppState.RECORDING: "录音中…",
    AppState.TRANSCRIBING: "识别中…",
    AppState.DONE: "已复制",
    AppState.ERROR: "出错",
}

# 图标颜色
COLOR_IDLE = (128, 128, 128, 255)       # 灰
COLOR_RECORDING = (220, 50, 50, 255)    # 红
COLOR_BUSY = (220, 180, 40, 255)        # 黄
COLOR_DONE = (50, 180, 80, 255)         # 绿
COLOR_ERROR = (180, 40, 40, 255)


def make_icon(color: tuple[int, int, int, int], size: int = 64) -> Image.Image:
    """程序化生成圆形托盘图标。"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    margin = max(2, size // 16)
    draw.ellipse([margin, margin, size - margin - 1, size - margin - 1], fill=color)
    # 内圈高光
    inner = size // 4
    highlight = (
        min(255, color[0] + 40),
        min(255, color[1] + 40),
        min(255, color[2] + 40),
        180,
    )
    draw.ellipse(
        [inner, inner // 2, size // 2, size // 2],
        fill=highlight,
    )
    return img


def _beep() -> None:
    """简短提示音。"""
    try:
        if platform.system() == "Windows":
            import winsound

            winsound.MessageBeep(winsound.MB_OK)
        else:
            # Linux 终端响铃
            sys.stdout.write("\a")
            sys.stdout.flush()
    except Exception:
        pass


def _notify(title: str, message: str) -> None:
    """桌面通知（plyer 可选）。"""
    try:
        from plyer import notification

        notification.notify(
            title=title,
            message=message[:200],
            app_name="WhisperTray",
            timeout=3,
        )
        return
    except Exception as e:
        logger.debug("plyer 通知不可用: %s", e)

    # Windows 托盘 balloon 由 pystray 的 notify 承担（若支持）
    logger.info("通知: %s — %s", title, message)


class TrayApp:
    def __init__(self) -> None:
        self.config = Config()
        self.state = AppState.LOADING
        self._icon = None  # pystray.Icon
        self._lock = threading.Lock()
        self._busy = False  # 防止重复点击

        self.recorder = Recorder(
            sample_rate=int(self.config.get("sample_rate", 16000)),
            channels=int(self.config.get("channels", 1)),
            recordings_dir=get_recordings_dir(),
        )
        self.recorder.set_error_callback(self._on_recorder_error)

        device, compute = self.config.resolve_device_and_compute()
        self.transcriber = Transcriber(
            model_name=self.config.model,
            language=self.config.language,
            device=self.config.get("device", "auto"),
            compute_type=self.config.get("compute_type", "auto"),
            beam_size=int(self.config.get("beam_size", 5)),
            vad_filter=bool(self.config.get("vad_filter", True)),
        )
        self.transcriber.set_progress_callback(lambda m: logger.info("[ASR] %s", m))

        self._icons = {
            AppState.LOADING: make_icon(COLOR_BUSY),
            AppState.IDLE: make_icon(COLOR_IDLE),
            AppState.RECORDING: make_icon(COLOR_RECORDING),
            AppState.TRANSCRIBING: make_icon(COLOR_BUSY),
            AppState.DONE: make_icon(COLOR_DONE),
            AppState.ERROR: make_icon(COLOR_ERROR),
        }
        self._last_transcript = ""
        self._last_transcript_path = get_data_dir() / "last_transcript.txt"

        logger.info(
            "数据目录: %s | 默认模型=%s 语言=%s 设备偏好=%s/%s",
            get_data_dir(),
            self.config.model,
            self.config.language,
            device,
            compute,
        )

    # ---------- UI 状态 ----------

    def _title(self) -> str:
        base = STATE_TITLES.get(self.state, "WhisperTray")
        extra = f" [{self.config.model}/{self.config.language}]"
        return f"WhisperTray — {base}{extra}"

    def _set_state(self, state: AppState) -> None:
        self.state = state
        if self._icon is not None:
            try:
                self._icon.icon = self._icons[state]
                self._icon.title = self._title()
            except Exception as e:
                logger.debug("更新图标失败: %s", e)

    def _on_recorder_error(self, msg: str) -> None:
        self._set_state(AppState.ERROR)
        _notify("WhisperTray", msg)
        # 短暂显示错误后回到空闲
        threading.Timer(2.0, lambda: self._set_state(AppState.IDLE)).start()

    # ---------- 菜单 ----------

    def _build_menu(self):
        import pystray

        def model_item(name: str):
            return pystray.MenuItem(
                name,
                lambda: self._change_model(name),
                checked=lambda item: self.config.model == name,
                radio=True,
            )

        def lang_item(code: str, label: str):
            return pystray.MenuItem(
                label,
                lambda: self._change_language(code),
                checked=lambda item: self.config.language == code,
                radio=True,
            )

        model_menu = pystray.Menu(*[model_item(m) for m in AVAILABLE_MODELS])
        lang_menu = pystray.Menu(
            *[lang_item(code, label) for code, label in AVAILABLE_LANGUAGES.items()]
        )

        toggle_text = (
            "停止录音"
            if self.state == AppState.RECORDING
            else "开始录音"
        )

        return pystray.Menu(
            pystray.MenuItem(toggle_text, self._toggle_recording, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("选择模型", model_menu),
            pystray.MenuItem("选择语言", lang_menu),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("打开日志目录", self._open_logs),
            pystray.MenuItem("打开数据目录", self._open_data),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self._quit),
        )

    def _refresh_menu(self) -> None:
        if self._icon is not None:
            try:
                self._icon.menu = self._build_menu()
                self._icon.update_menu()
            except Exception as e:
                logger.debug("刷新菜单失败: %s", e)

    # ---------- 动作 ----------

    def _toggle_recording(self, icon=None, item=None) -> None:  # noqa: ARG002
        if self.state == AppState.LOADING:
            _notify("WhisperTray", "模型仍在加载，请稍候…")
            return
        if self.state == AppState.TRANSCRIBING:
            return

        with self._lock:
            if self._busy and self.state != AppState.RECORDING:
                return

        if self.state == AppState.RECORDING:
            self._stop_and_transcribe()
        else:
            self._start_recording()

    def _start_recording(self) -> None:
        if not self.transcriber.is_ready:
            _notify("WhisperTray", "模型未就绪，无法录音")
            return
        ok = self.recorder.start()
        if ok:
            self._set_state(AppState.RECORDING)
            self._refresh_menu()
            logger.info("进入录音状态")

    def _stop_and_transcribe(self) -> None:
        with self._lock:
            if self._busy:
                return
            self._busy = True

        wav_path = self.recorder.stop()
        self._refresh_menu()

        if wav_path is None:
            self._set_state(AppState.IDLE)
            with self._lock:
                self._busy = False
            _notify("WhisperTray", "录音为空或失败")
            return

        self._set_state(AppState.TRANSCRIBING)
        threading.Thread(
            target=self._transcribe_worker,
            args=(wav_path,),
            daemon=True,
            name="transcribe",
        ).start()

    def _transcribe_worker(self, wav_path: Path) -> None:
        try:
            text = self.transcriber.transcribe(wav_path)
            self._last_transcript = text
            try:
                self._last_transcript_path.write_text(text, encoding="utf-8")
            except Exception as e:
                logger.warning("保存上次转写失败: %s", e)

            if text:
                copied = copy_to_clipboard(text)
                self._set_state(AppState.DONE)
                preview = text if len(text) <= 80 else text[:80] + "…"
                msg = f"已复制到剪贴板:\n{preview}" if copied else f"识别完成但复制失败:\n{preview}"
                if self.config.get("notify", True):
                    _notify("WhisperTray", msg)
                _beep()
                # 2 秒后恢复空闲
                time.sleep(2.0)
                self._set_state(AppState.IDLE)
            else:
                self._set_state(AppState.ERROR)
                _notify("WhisperTray", "识别结果为空")
                time.sleep(2.0)
                self._set_state(AppState.IDLE)
        finally:
            with self._lock:
                self._busy = False

    def _change_model(self, name: str) -> None:
        if name == self.config.model:
            return
        if self.state in (AppState.RECORDING, AppState.TRANSCRIBING, AppState.LOADING):
            _notify("WhisperTray", "请等待当前操作完成后再切换模型")
            return

        self.config.model = name
        self._set_state(AppState.LOADING)
        self._refresh_menu()
        _notify("WhisperTray", f"正在加载模型 {name}…")

        def worker():
            ok = self.transcriber.reload(model_name=name)
            self._set_state(AppState.IDLE if ok else AppState.ERROR)
            self._refresh_menu()
            if ok:
                _notify("WhisperTray", f"模型 {name} 已就绪")
            else:
                _notify("WhisperTray", f"模型加载失败: {self.transcriber.load_error}")

        threading.Thread(target=worker, daemon=True, name="reload-model").start()

    def _change_language(self, code: str) -> None:
        if code == self.config.language:
            return
        self.config.language = code
        self.transcriber.language = code
        self._refresh_menu()
        if self._icon:
            self._icon.title = self._title()
        label = AVAILABLE_LANGUAGES.get(code, code)
        logger.info("语言已切换: %s", label)
        _notify("WhisperTray", f"语言: {label}")

    def _open_logs(self, icon=None, item=None) -> None:  # noqa: ARG002
        self._open_path(get_logs_dir())

    def _open_data(self, icon=None, item=None) -> None:  # noqa: ARG002
        self._open_path(get_data_dir())

    @staticmethod
    def _open_path(path: Path) -> None:
        path.mkdir(parents=True, exist_ok=True)
        try:
            system = platform.system()
            if system == "Windows":
                subprocess.Popen(["explorer", str(path)])
            elif system == "Darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            logger.error("打开目录失败: %s", e)

    def _quit(self, icon=None, item=None) -> None:  # noqa: ARG002
        logger.info("退出应用")
        if self.recorder.is_recording:
            self.recorder.stop()
        if self._icon is not None:
            self._icon.stop()

    # ---------- 启动 ----------

    def _load_model_async(self) -> None:
        ok = self.transcriber.load()
        self._set_state(AppState.IDLE if ok else AppState.ERROR)
        self._refresh_menu()
        if ok:
            logger.info("应用就绪")
        else:
            _notify("WhisperTray", f"模型加载失败: {self.transcriber.load_error}")

    def run(self) -> None:
        import pystray

        # 左键点击 = 默认菜单项（toggle）
        self._icon = pystray.Icon(
            name="WhisperTray",
            icon=self._icons[AppState.LOADING],
            title=self._title(),
            menu=self._build_menu(),
        )

        threading.Thread(
            target=self._load_model_async,
            daemon=True,
            name="load-model",
        ).start()

        logger.info("托盘图标已启动")
        self._icon.run()
