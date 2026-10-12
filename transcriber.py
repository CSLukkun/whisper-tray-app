"""faster-whisper 转写：启动时加载模型并保持热态。"""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class Transcriber:
    """线程安全的 Whisper 转写器。"""

    def __init__(
        self,
        model_name: str = "small",
        language: str = "zh",
        device: str = "auto",
        compute_type: str = "auto",
        beam_size: int = 5,
        vad_filter: bool = True,
    ) -> None:
        self.model_name = model_name
        self.language = language
        self.device_pref = device
        self.compute_type_pref = compute_type
        self.beam_size = beam_size
        self.vad_filter = vad_filter

        self._model = None
        self._lock = threading.RLock()
        self._ready = threading.Event()
        self._load_error: Optional[str] = None
        self._device: str = "cpu"
        self._compute_type: str = "int8"
        self._on_progress: Optional[Callable[[str], None]] = None

    def set_progress_callback(self, cb: Callable[[str], None]) -> None:
        self._on_progress = cb

    def _progress(self, msg: str) -> None:
        logger.info(msg)
        if self._on_progress:
            try:
                self._on_progress(msg)
            except Exception:
                pass

    @property
    def is_ready(self) -> bool:
        return self._ready.is_set() and self._model is not None

    @property
    def load_error(self) -> Optional[str]:
        return self._load_error

    @property
    def device_info(self) -> str:
        return f"{self._device}/{self._compute_type}"

    def _resolve_device(self) -> tuple[str, str]:
        device = self.device_pref
        compute_type = self.compute_type_pref

        if device == "auto":
            try:
                import ctranslate2

                device = "cuda" if ctranslate2.get_cuda_device_count() > 0 else "cpu"
            except Exception:
                device = "cpu"

        if compute_type == "auto":
            compute_type = "float16" if device == "cuda" else "int8"

        return device, compute_type

    def load(self) -> bool:
        """加载（或重新加载）模型。阻塞调用，适合放在后台线程。"""
        with self._lock:
            self._ready.clear()
            self._load_error = None
            self._model = None

            device, compute_type = self._resolve_device()
            self._device = device
            self._compute_type = compute_type

            self._progress(
                f"正在加载模型 {self.model_name} "
                f"(device={device}, compute={compute_type})…"
            )
            self._progress(
                "首次使用会下载模型（small 约 500MB），请耐心等待…"
            )

            try:
                from faster_whisper import WhisperModel

                self._model = WhisperModel(
                    self.model_name,
                    device=device,
                    compute_type=compute_type,
                )
                self._ready.set()
                self._progress(
                    f"模型已就绪: {self.model_name} ({device}/{compute_type})"
                )
                return True
            except Exception as e:
                # CUDA 失败时回退 CPU
                if device == "cuda":
                    logger.warning("CUDA 加载失败，回退 CPU/int8: %s", e)
                    try:
                        from faster_whisper import WhisperModel

                        self._device = "cpu"
                        self._compute_type = "int8"
                        self._model = WhisperModel(
                            self.model_name,
                            device="cpu",
                            compute_type="int8",
                        )
                        self._ready.set()
                        self._progress(
                            f"模型已就绪(CPU回退): {self.model_name} (cpu/int8)"
                        )
                        return True
                    except Exception as e2:
                        self._load_error = str(e2)
                        logger.exception("模型加载失败")
                        self._progress(f"模型加载失败: {e2}")
                        return False

                self._load_error = str(e)
                logger.exception("模型加载失败")
                self._progress(f"模型加载失败: {e}")
                return False

    def reload(
        self,
        model_name: Optional[str] = None,
        language: Optional[str] = None,
    ) -> bool:
        """切换模型/语言并重新加载。"""
        with self._lock:
            if model_name:
                self.model_name = model_name
            if language is not None:
                self.language = language
        return self.load()

    def wait_ready(self, timeout: Optional[float] = None) -> bool:
        return self._ready.wait(timeout=timeout)

    def transcribe(self, audio_path: Path | str) -> str:
        """转写音频文件，返回文本。未就绪或失败返回空字符串。"""
        path = Path(audio_path)
        if not path.exists():
            logger.error("音频文件不存在: %s", path)
            return ""

        if not self.wait_ready(timeout=600):
            logger.error("模型未就绪: %s", self._load_error)
            return ""

        with self._lock:
            if self._model is None:
                return ""

            lang = None if self.language == "auto" else self.language
            self._progress(f"开始识别: {path.name}")

            try:
                segments, info = self._model.transcribe(
                    str(path),
                    language=lang,
                    beam_size=self.beam_size,
                    vad_filter=self.vad_filter,
                )
                parts: list[str] = []
                for seg in segments:
                    text = (seg.text or "").strip()
                    if text:
                        parts.append(text)

                result = "".join(parts) if lang == "zh" else " ".join(parts)
                result = result.strip()

                detected = getattr(info, "language", lang or "?")
                logger.info(
                    "识别完成: lang=%s, 长度=%d, 预览=%s",
                    detected,
                    len(result),
                    result[:80],
                )
                if not result:
                    self._progress("识别结果为空（可能无语音）")
                return result
            except Exception as e:
                logger.exception("转写失败")
                self._progress(f"转写失败: {e}")
                return ""
