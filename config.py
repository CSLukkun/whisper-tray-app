"""配置管理：模型、语言、路径等。"""

from __future__ import annotations

import json
import logging
import os
import platform
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

APP_NAME = "WhisperTray"
DEFAULT_MODEL = "small"
DEFAULT_LANGUAGE = "zh"  # 自动可用 "auto"；中文友好默认 zh
AVAILABLE_MODELS = ("tiny", "base", "small", "medium")
AVAILABLE_LANGUAGES = {
    "auto": "自动检测",
    "zh": "中文",
    "en": "英语",
}


def get_data_dir() -> Path:
    """Windows 用 %LOCALAPPDATA%/WhisperTray，其它平台用 ~/.whisper-tray。"""
    if platform.system() == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(base) / APP_NAME
    else:
        path = Path.home() / ".whisper-tray"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_recordings_dir() -> Path:
    d = get_data_dir() / "recordings"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_logs_dir() -> Path:
    d = get_data_dir() / "logs"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_config_path() -> Path:
    return get_data_dir() / "config.json"


DEFAULT_CONFIG: dict[str, Any] = {
    "model": DEFAULT_MODEL,
    "language": DEFAULT_LANGUAGE,
    "device": "auto",  # auto | cpu | cuda
    "compute_type": "auto",  # auto | int8 | float16 | float32
    "hotkey": None,  # 预留：全局热键
    "sample_rate": 16000,
    "channels": 1,
    "beam_size": 5,
    "vad_filter": True,
    "notify": True,
}


class Config:
    def __init__(self) -> None:
        self._data: dict[str, Any] = dict(DEFAULT_CONFIG)
        self.load()

    def load(self) -> None:
        path = get_config_path()
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if isinstance(loaded, dict):
                    self._data.update(loaded)
                    logger.info("已加载配置: %s", path)
            except Exception as e:
                logger.warning("读取配置失败，使用默认值: %s", e)
        else:
            self.save()

    def save(self) -> None:
        path = get_config_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
            logger.info("配置已保存: %s", path)
        except Exception as e:
            logger.error("保存配置失败: %s", e)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any, persist: bool = True) -> None:
        self._data[key] = value
        if persist:
            self.save()

    @property
    def model(self) -> str:
        m = self._data.get("model", DEFAULT_MODEL)
        return m if m in AVAILABLE_MODELS else DEFAULT_MODEL

    @model.setter
    def model(self, value: str) -> None:
        if value not in AVAILABLE_MODELS:
            raise ValueError(f"不支持的模型: {value}")
        self.set("model", value)

    @property
    def language(self) -> str:
        lang = self._data.get("language", DEFAULT_LANGUAGE)
        return lang if lang in AVAILABLE_LANGUAGES else DEFAULT_LANGUAGE

    @language.setter
    def language(self, value: str) -> None:
        if value not in AVAILABLE_LANGUAGES:
            raise ValueError(f"不支持的语言: {value}")
        self.set("language", value)

    def resolve_device_and_compute(self) -> tuple[str, str]:
        """返回 (device, compute_type)。auto 时探测 CUDA。"""
        device = self.get("device", "auto")
        compute_type = self.get("compute_type", "auto")

        if device == "auto":
            try:
                import ctranslate2

                cuda_count = ctranslate2.get_cuda_device_count()
                device = "cuda" if cuda_count > 0 else "cpu"
            except Exception:
                device = "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        return device, compute_type
