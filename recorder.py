"""麦克风录音：sounddevice + numpy，写入 WAV。"""

from __future__ import annotations

import logging
import threading
import wave
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

import numpy as np

logger = logging.getLogger(__name__)


class Recorder:
    """线程安全的录音器。"""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        recordings_dir: Optional[Path] = None,
    ) -> None:
        self.sample_rate = sample_rate
        self.channels = channels
        self.recordings_dir = recordings_dir
        self._lock = threading.Lock()
        self._recording = False
        self._frames: list[np.ndarray] = []
        self._stream = None
        self._sd = None
        self._on_error: Optional[Callable[[str], None]] = None

    def set_error_callback(self, cb: Callable[[str], None]) -> None:
        self._on_error = cb

    @property
    def is_recording(self) -> bool:
        with self._lock:
            return self._recording

    def _emit_error(self, msg: str) -> None:
        logger.error(msg)
        if self._on_error:
            try:
                self._on_error(msg)
            except Exception:
                pass

    def _callback(self, indata, frames, time_info, status) -> None:  # noqa: ARG002
        if status:
            logger.warning("录音状态: %s", status)
        with self._lock:
            if self._recording:
                self._frames.append(indata.copy())

    def start(self) -> bool:
        """开始录音。成功返回 True。"""
        with self._lock:
            if self._recording:
                logger.warning("已在录音中")
                return False

        try:
            import sounddevice as sd

            self._sd = sd
        except ImportError as e:
            self._emit_error(f"无法导入 sounddevice: {e}")
            return False

        with self._lock:
            self._frames = []
            self._recording = True

        try:
            self._stream = self._sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype="float32",
                callback=self._callback,
            )
            self._stream.start()
            logger.info(
                "开始录音: rate=%d channels=%d",
                self.sample_rate,
                self.channels,
            )
            return True
        except Exception as e:
            with self._lock:
                self._recording = False
                self._frames = []
            self._stream = None
            msg = (
                f"无法打开麦克风: {e}。"
                "请检查麦克风权限与默认录音设备。"
            )
            self._emit_error(msg)
            return False

    def stop(self) -> Optional[Path]:
        """停止录音并保存 WAV。返回文件路径；无有效音频返回 None。"""
        with self._lock:
            if not self._recording:
                logger.warning("当前未在录音")
                return None
            self._recording = False
            frames = list(self._frames)
            self._frames = []

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.warning("关闭录音流失败: %s", e)
            finally:
                self._stream = None

        if not frames:
            logger.warning("录音为空（无音频帧）")
            return None

        audio = np.concatenate(frames, axis=0)
        if audio.size == 0:
            logger.warning("录音为空（零长度）")
            return None

        # 检测几乎静音
        peak = float(np.max(np.abs(audio)))
        if peak < 1e-5:
            logger.warning("录音几乎静音 (peak=%.2e)", peak)

        if self.recordings_dir is None:
            from config import get_recordings_dir

            self.recordings_dir = get_recordings_dir()

        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        wav_path = self.recordings_dir / f"rec_{ts}.wav"

        # float32 -> int16 PCM
        audio_i16 = np.clip(audio, -1.0, 1.0)
        audio_i16 = (audio_i16 * 32767.0).astype(np.int16)

        try:
            with wave.open(str(wav_path), "wb") as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(2)
                wf.setframerate(self.sample_rate)
                wf.writeframes(audio_i16.tobytes())
            duration = len(audio) / float(self.sample_rate)
            logger.info("录音已保存: %s (%.2fs, peak=%.3f)", wav_path, duration, peak)
            return wav_path
        except Exception as e:
            self._emit_error(f"保存 WAV 失败: {e}")
            return None
