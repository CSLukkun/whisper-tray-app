#!/usr/bin/env python3
"""Generate WhisperTray product demo frames, then assemble with ffmpeg."""
from __future__ import annotations

import math
import os
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --- Config ---
W, H = 960, 540
FPS = 24
ROOT = Path("/workspace/whisper-tray-app")
DOCS = ROOT / "docs"
FRAMES = Path("/tmp/whisper-demo-frames")
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"

# App colors from tray_app.py
COLOR_IDLE = (128, 128, 128)
COLOR_RECORDING = (220, 50, 50)
COLOR_BUSY = (220, 180, 40)
COLOR_DONE = (50, 180, 80)

# Windows 11-ish palette (dark)
DESKTOP_BG = (32, 36, 48)
TASKBAR_BG = (24, 26, 34, 230)
PANEL_BG = (45, 48, 62)
PANEL_BORDER = (70, 74, 92)
TEXT = (240, 242, 248)
TEXT_DIM = (160, 168, 184)
ACCENT = (96, 165, 250)
TOAST_BG = (38, 42, 56)
NOTEPAD_BG = (250, 250, 252)
NOTEPAD_TITLE = (243, 243, 243)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    path = FONT_BOLD if bold else FONT_REG
    return ImageFont.truetype(path, size=size, index=0)


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_color(c1, c2, t):
    return tuple(int(lerp(a, b, t)) for a, b in zip(c1, c2))


def draw_rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def draw_tray_icon(img: Image.Image, cx: int, cy: int, color, size: int = 22, pulse: float = 0.0):
    """Circular tray icon matching app style."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    r = size // 2
    if pulse > 0:
        pr = int(r + 6 + pulse * 8)
        alpha = int(80 * (1 - pulse))
        glow = (*color[:3], alpha)
        d.ellipse([cx - pr, cy - pr, cx + pr, cy + pr], fill=glow)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, 255))
    # highlight
    hr = r // 2
    hl = (
        min(255, color[0] + 40),
        min(255, color[1] + 40),
        min(255, color[2] + 40),
        180,
    )
    d.ellipse([cx - hr, cy - hr - 2, cx, cy], fill=hl)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def draw_desktop_base(show_taskbar=True) -> Image.Image:
    img = Image.new("RGBA", (W, H), (*DESKTOP_BG, 255))
    d = ImageDraw.Draw(img)
    # subtle gradient wallpaper feel
    for y in range(H):
        t = y / H
        c = lerp_color((28, 32, 48), (40, 44, 64), t)
        d.line([(0, y), (W, y)], fill=(*c, 255))
    # faint decorative circles
    for cx, cy, r, a in [(120, 100, 180, 18), (820, 200, 220, 12), (400, 400, 150, 10)]:
        overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        od.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(80, 120, 200, a))
        img = Image.alpha_composite(img, overlay)
        d = ImageDraw.Draw(img)

    if show_taskbar:
        tb_h = 44
        # taskbar
        bar = Image.new("RGBA", (W, tb_h), TASKBAR_BG)
        img.paste(bar, (0, H - tb_h), bar)
        d = ImageDraw.Draw(img)
        # start / search faux icons
        sx = 18
        d.rounded_rectangle([sx, H - 32, sx + 20, H - 12], radius=4, fill=(70, 130, 220, 220))
        d.rounded_rectangle([sx + 30, H - 30, sx + 160, H - 14], radius=8, fill=(50, 54, 68, 200))
        d.text((sx + 42, H - 29), "搜索", font=font(11), fill=TEXT_DIM)
        # clock
        d.text((W - 70, H - 30), "22:50", font=font(12), fill=TEXT)
    return img


def draw_tooltip(img, text, near_x, near_y, color=None):
    d = ImageDraw.Draw(img)
    f = font(13)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad_x, pad_y = 10, 6
    tip_w, tip_h = tw + pad_x * 2, th + pad_y * 2
    x = near_x - tip_w // 2
    y = near_y - tip_h - 14
    x = max(8, min(W - tip_w - 8, x))
    draw_rounded_rect(d, [x, y, x + tip_w, y + tip_h], 6, fill=(30, 32, 42, 240), outline=PANEL_BORDER)
    if color:
        # small color dot
        d.ellipse([x + 8, y + tip_h // 2 - 4, x + 16, y + tip_h // 2 + 4], fill=(*color, 255))
        d.text((x + 20, y + pad_y - 1), text, font=f, fill=TEXT)
    else:
        d.text((x + pad_x, y + pad_y - 1), text, font=f, fill=TEXT)
    return img


def draw_waveform(d, cx, cy, w, h, t, active=True):
    bars = 24
    bw = w // bars - 2
    for i in range(bars):
        phase = t * 8 + i * 0.45
        amp = (0.35 + 0.65 * abs(math.sin(phase))) if active else 0.15
        # emphasize middle
        amp *= 0.5 + 0.5 * math.sin(math.pi * i / (bars - 1))
        bh = max(4, int(h * amp))
        x0 = cx - w // 2 + i * (bw + 2)
        y0 = cy - bh // 2
        color = COLOR_RECORDING if active else (90, 94, 110)
        d.rounded_rectangle([x0, y0, x0 + bw, y0 + bh], radius=2, fill=(*color, 230))


def draw_cursor(img, x, y, clicking=False):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    # simple arrow cursor
    pts = [(x, y), (x, y + 18), (x + 5, y + 14), (x + 9, y + 22), (x + 12, y + 20), (x + 7, y + 12), (x + 14, y + 12)]
    fill = (255, 255, 255, 255) if not clicking else (255, 220, 120, 255)
    d.polygon(pts, fill=fill, outline=(20, 20, 30, 255))
    if clicking:
        r = 14
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 200, 80, 160), width=2)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def draw_toast(img, title, body, progress=1.0):
    """Bottom-right toast notification."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    tw, th = 320, 88
    x = W - tw - 20
    y = H - 44 - th - 16
    # slide-in based on progress
    slide = int((1 - min(1, progress * 1.5)) * 40)
    y += slide
    alpha_boost = int(255 * min(1, progress * 2))
    draw_rounded_rect(d, [x, y, x + tw, y + th], 10, fill=(*TOAST_BG, min(245, alpha_boost)), outline=(*PANEL_BORDER, 200))
    # green check circle
    d.ellipse([x + 14, y + 28, x + 42, y + 56], fill=(*COLOR_DONE, 255))
    d.line([(x + 22, y + 42), (x + 28, y + 48), (x + 36, y + 34)], fill=(255, 255, 255, 255), width=3)
    f_title = font(14, bold=True)
    f_body = font(13)
    d.text((x + 54, y + 18), title, font=f_title, fill=TEXT)
    # wrap body
    d.text((x + 54, y + 42), body, font=f_body, fill=TEXT_DIM)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def draw_notepad(img, text_content: str, caret_blink: bool, typing_chars: int):
    """Simple Notepad-like window center."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    nw, nh = 520, 300
    nx, ny = (W - nw) // 2, (H - nh) // 2 - 20
    # shadow
    sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([nx + 6, ny + 8, nx + nw + 6, ny + nh + 8], radius=8, fill=(0, 0, 0, 60))
    overlay = Image.alpha_composite(overlay, sh)
    d = ImageDraw.Draw(overlay)

    draw_rounded_rect(d, [nx, ny, nx + nw, ny + nh], 8, fill=(*NOTEPAD_BG, 255), outline=(180, 180, 190, 255))
    # title bar
    d.rounded_rectangle([nx, ny, nx + nw, ny + 32], radius=8, fill=(*NOTEPAD_TITLE, 255))
    d.rectangle([nx, ny + 20, nx + nw, ny + 32], fill=(*NOTEPAD_TITLE, 255))
    d.text((nx + 12, ny + 7), "无标题 - 记事本", font=font(12), fill=(40, 40, 50))
    # window buttons
    for i, c in enumerate([(232, 17, 35), (200, 200, 200), (200, 200, 200)]):
        bx = nx + nw - 18 - i * 28
        d.ellipse([bx - 5, ny + 11, bx + 5, ny + 21], fill=(*c, 255) if i == 0 else (200, 200, 205, 255))

    # menu strip
    d.rectangle([nx + 1, ny + 32, nx + nw - 1, ny + 54], fill=(245, 245, 248, 255))
    d.text((nx + 12, ny + 36), "文件  编辑  格式  查看  帮助", font=font(11), fill=(60, 60, 70))

    # content
    shown = text_content[:typing_chars]
    f = font(18)
    d.text((nx + 20, ny + 70), shown, font=f, fill=(20, 20, 30))
    if caret_blink and typing_chars <= len(text_content):
        # caret after text
        bb = d.textbbox((nx + 20, ny + 70), shown, font=f)
        cx = bb[2] + 1
        d.line([(cx, ny + 72), (cx, ny + 72 + 22)], fill=(20, 20, 30), width=2)

    # status hint
    if typing_chars == 0:
        d.text((nx + 20, ny + 70), "按 Ctrl+V 粘贴…", font=font(14), fill=(160, 160, 170))
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def draw_mic_badge(img, cx, cy, pulse):
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    r = 36 + int(pulse * 6)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 50, 50, int(40 + pulse * 40)))
    d.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(220, 50, 50, 220))
    # mic shape
    d.rounded_rectangle([cx - 8, cy - 14, cx + 8, cy + 6], radius=8, fill=(255, 255, 255, 255))
    d.arc([cx - 14, cy - 4, cx + 14, cy + 18], 0, 180, fill=(255, 255, 255, 255), width=3)
    d.line([(cx, cy + 18), (cx, cy + 24)], fill=(255, 255, 255, 255), width=3)
    d.line([(cx - 8, cy + 24), (cx + 8, cy + 24)], fill=(255, 255, 255, 255), width=3)
    return Image.alpha_composite(img.convert("RGBA"), overlay)


def draw_caption_bubble(img, text, y=120):
    d = ImageDraw.Draw(img)
    f = font(20)
    bbox = d.textbbox((0, 0), text, font=f)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    pad = 16
    bw, bh = tw + pad * 2, th + pad
    x = (W - bw) // 2
    draw_rounded_rect(d, [x, y, x + bw, y + bh], 12, fill=(20, 22, 32, 220), outline=(90, 100, 130, 180))
    d.text((x + pad, y + pad // 2), text, font=f, fill=TEXT)
    # quote mark style
    d.text((x + 8, y - 2), "「", font=font(16), fill=ACCENT)
    return img


def title_card(t: float) -> Image.Image:
    """t in 0..1 over the scene."""
    img = Image.new("RGBA", (W, H), (*DESKTOP_BG, 255))
    d = ImageDraw.Draw(img)
    for y in range(H):
        c = lerp_color((24, 28, 42), (36, 42, 62), y / H)
        d.line([(0, y), (W, y)], fill=(*c, 255))

    fade = min(1.0, t * 3) if t < 0.85 else max(0, 1 - (t - 0.85) / 0.15)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    # icon
    ic = (W // 2, H // 2 - 70)
    r = 36
    od.ellipse([ic[0] - r, ic[1] - r, ic[0] + r, ic[1] + r], fill=(*COLOR_IDLE, int(255 * fade)))
    od.ellipse([ic[0] - 14, ic[1] - 18, ic[0] + 2, ic[1] - 2], fill=(168, 168, 168, int(180 * fade)))

    title = "WhisperTray"
    subtitle = "说完就复制"
    f1 = font(42, bold=True)
    f2 = font(24)
    bb = od.textbbox((0, 0), title, font=f1)
    tw = bb[2] - bb[0]
    od.text(((W - tw) // 2, H // 2 - 10), title, font=f1, fill=(*TEXT, int(255 * fade)))
    bb2 = od.textbbox((0, 0), subtitle, font=f2)
    tw2 = bb2[2] - bb2[0]
    od.text(((W - tw2) // 2, H // 2 + 48), subtitle, font=f2, fill=(*TEXT_DIM, int(255 * fade)))
    # accent line
    lw = int(80 * fade)
    od.rectangle([W // 2 - lw, H // 2 + 40, W // 2 + lw, H // 2 + 43], fill=(*ACCENT, int(200 * fade)))
    return Image.alpha_composite(img, overlay)


def end_card(t: float) -> Image.Image:
    img = Image.new("RGBA", (W, H), (*DESKTOP_BG, 255))
    d = ImageDraw.Draw(img)
    for y in range(H):
        c = lerp_color((24, 28, 42), (36, 42, 62), y / H)
        d.line([(0, y), (W, y)], fill=(*c, 255))
    fade = min(1.0, t * 4)
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    lines = [
        ("github.com/CSLukkun/whisper-tray-app", font(22, bold=True), TEXT),
        ("本地 Whisper · 免 Python 可打包", font(18), TEXT_DIM),
    ]
    y0 = H // 2 - 40
    for i, (txt, f, col) in enumerate(lines):
        bb = od.textbbox((0, 0), txt, font=f)
        tw = bb[2] - bb[0]
        od.text(((W - tw) // 2, y0 + i * 44), txt, font=f, fill=(*col, int(255 * fade)))
    # green done icon
    cx, cy = W // 2, H // 2 - 90
    od.ellipse([cx - 28, cy - 28, cx + 28, cy + 28], fill=(*COLOR_DONE, int(255 * fade)))
    od.line([(cx - 10, cy), (cx - 2, cy + 10), (cx + 12, cy - 10)], fill=(255, 255, 255, int(255 * fade)), width=4)
    return Image.alpha_composite(img, overlay)


def scene_idle_click(t: float) -> Image.Image:
    """Idle tray + cursor click. t 0..1"""
    img = draw_desktop_base()
    tray_x, tray_y = W - 100, H - 22
    img = draw_tray_icon(img, tray_x, tray_y, COLOR_IDLE, size=20)
    img = draw_tooltip(img, "空闲 / 点击录音", tray_x, tray_y - 8, COLOR_IDLE)

    # cursor moves toward tray then clicks
    start = (W // 2, H // 2)
    end = (tray_x - 4, tray_y - 6)
    if t < 0.55:
        p = t / 0.55
        # ease
        p = p * p * (3 - 2 * p)
        cx = int(lerp(start[0], end[0], p))
        cy = int(lerp(start[1], end[1], p))
        img = draw_cursor(img, cx, cy, clicking=False)
    else:
        click_t = (t - 0.55) / 0.45
        clicking = 0.15 < click_t < 0.55
        img = draw_cursor(img, end[0], end[1], clicking=clicking)
        if clicking:
            # click ripple
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(overlay)
            r = int(10 + click_t * 20)
            d.ellipse([end[0] - r, end[1] - r, end[0] + r, end[1] + r], outline=(255, 220, 100, 120), width=2)
            img = Image.alpha_composite(img, overlay)
    return img


def scene_recording(t: float) -> Image.Image:
    img = draw_desktop_base()
    tray_x, tray_y = W - 100, H - 22
    pulse = 0.5 + 0.5 * math.sin(t * math.pi * 4)
    img = draw_tray_icon(img, tray_x, tray_y, COLOR_RECORDING, size=20, pulse=pulse)
    img = draw_tooltip(img, "录音中…", tray_x, tray_y - 8, COLOR_RECORDING)

    # center panel with mic + waveform
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    pw, ph = 420, 200
    px, py = (W - pw) // 2, (H - ph) // 2 - 30
    draw_rounded_rect(d, [px, py, px + pw, py + ph], 14, fill=(*PANEL_BG, 235), outline=(*PANEL_BORDER, 200))
    img = Image.alpha_composite(img, overlay)
    img = draw_mic_badge(img, W // 2, py + 60, pulse * 0.5)

    d2 = ImageDraw.Draw(img)
    draw_waveform(d2, W // 2, py + 140, 300, 50, t * 5, active=True)

    # spoken caption appears progressively
    caption = "今天天气怎么样"
    chars = max(1, int(len(caption) * min(1.0, t / 0.7)))
    shown = caption[:chars]
    if t > 0.15:
        img = draw_caption_bubble(img, shown, y=py - 50)
    return img


def scene_transcribing(t: float) -> Image.Image:
    img = draw_desktop_base()
    tray_x, tray_y = W - 100, H - 22
    img = draw_tray_icon(img, tray_x, tray_y, COLOR_BUSY, size=20, pulse=0.3 + 0.3 * math.sin(t * 10))
    img = draw_tooltip(img, "识别中…", tray_x, tray_y - 8, COLOR_BUSY)

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(overlay)
    pw, ph = 360, 120
    px, py = (W - pw) // 2, (H - ph) // 2 - 20
    draw_rounded_rect(d, [px, py, px + pw, py + ph], 14, fill=(*PANEL_BG, 235), outline=(*PANEL_BORDER, 200))
    # spinner dots
    for i in range(3):
        ang = t * 6 + i * 2.1
        dx = int(math.cos(ang) * 18)
        dy = int(math.sin(ang) * 10)
        d.ellipse([W // 2 + dx - 6, py + 40 + dy - 6, W // 2 + dx + 6, py + 40 + dy + 6], fill=(*COLOR_BUSY, 230))
    d.text((px + 120, py + 78), "Whisper 识别中…", font=font(15), fill=TEXT_DIM)
    return Image.alpha_composite(img, overlay)


def scene_toast(t: float) -> Image.Image:
    img = draw_desktop_base()
    tray_x, tray_y = W - 100, H - 22
    img = draw_tray_icon(img, tray_x, tray_y, COLOR_DONE, size=20)
    img = draw_tooltip(img, "已复制", tray_x, tray_y - 8, COLOR_DONE)
    img = draw_toast(img, "已复制到剪贴板", "今天天气怎么样", progress=t)
    return img


def scene_paste(t: float) -> Image.Image:
    img = draw_desktop_base()
    tray_x, tray_y = W - 100, H - 22
    img = draw_tray_icon(img, tray_x, tray_y, COLOR_IDLE, size=20)

    text = "今天天气怎么样"
    # show shortcut flash then type/paste
    if t < 0.25:
        chars = 0
        # Ctrl+V badge
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)
        badge = "Ctrl + V"
        f = font(16, bold=True)
        bb = d.textbbox((0, 0), badge, font=f)
        tw = bb[2] - bb[0]
        bx = (W - tw) // 2 - 16
        by = H // 2 + 120
        draw_rounded_rect(d, [bx, by, bx + tw + 32, by + 36], 8, fill=(30, 32, 42, 230), outline=(*ACCENT, 200))
        d.text((bx + 16, by + 8), badge, font=f, fill=TEXT)
        img = Image.alpha_composite(img, overlay)
    else:
        p = (t - 0.25) / 0.75
        chars = int(len(text) * min(1.0, p * 1.2))
    blink = int(t * 4) % 2 == 0
    img = draw_notepad(img, text, caret_blink=blink, typing_chars=chars)
    return img


# Scene durations (seconds)
SCENES = [
    ("title", 2.0, title_card),
    ("idle", 2.0, scene_idle_click),
    ("record", 5.0, scene_recording),
    ("transcribe", 2.0, scene_transcribing),
    ("toast", 3.0, scene_toast),
    ("paste", 3.0, scene_paste),
    ("end", 2.0, end_card),
]


def render_all():
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir(parents=True)
    DOCS.mkdir(parents=True, exist_ok=True)

    frame_idx = 0
    all_frame_paths = []
    for name, dur, fn in SCENES:
        n = int(dur * FPS)
        print(f"Rendering {name}: {n} frames ({dur}s)")
        for i in range(n):
            t = i / max(1, n - 1)
            img = fn(t)
            # ensure RGB for ffmpeg
            out = img.convert("RGB")
            path = FRAMES / f"frame_{frame_idx:05d}.png"
            out.save(path, "PNG")
            all_frame_paths.append(path)
            frame_idx += 1
    print(f"Total frames: {frame_idx}")
    return frame_idx


def assemble(total_frames: int):
    mp4 = DOCS / "demo.mp4"
    gif = DOCS / "demo.gif"
    poster = DOCS / "demo-poster.png"

    # Poster: pick a nice mid recording frame (~ title 2s + idle 2s + 2s into record)
    poster_idx = int((2 + 2 + 2) * FPS)
    poster_src = FRAMES / f"frame_{poster_idx:05d}.png"
    Image.open(poster_src).save(poster, "PNG")
    print(f"Poster: {poster}")

    # MP4 H.264
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", str(FRAMES / "frame_%05d.png"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-crf", "23",
        "-movflags", "+faststart",
        "-an",
        str(mp4),
    ]
    subprocess.run(cmd, check=True)
    print(f"MP4: {mp4} ({mp4.stat().st_size / 1024:.1f} KB)")

    # GIF: shorter loop — title(skip shorten) use idle→toast (~12s) at lower fps/size
    # Extract frames for GIF: from idle through toast (skip long title/end, trim record)
    # Build a compact timeline of selected frames
    gif_frames_dir = Path("/tmp/whisper-demo-gif")
    if gif_frames_dir.exists():
        shutil.rmtree(gif_frames_dir)
    gif_frames_dir.mkdir()

    # Map: use scenes idle(2) + record(4 of 5) + transcribe(2) + toast(2 of 3) ≈ 10s
    # Frame ranges in full render:
    # title 0..47, idle 48..95, record 96..215, transcribe 216..263, toast 264..335, paste 336..407, end 408..455
    ranges = []
    # short title 0.5s
    ranges += list(range(0, int(0.5 * FPS)))
    # idle full
    ranges += list(range(int(2 * FPS), int(4 * FPS)))
    # record 4s (skip last 1s of 5)
    ranges += list(range(int(4 * FPS), int(8 * FPS)))
    # transcribe full 2s
    ranges += list(range(int(9 * FPS), int(11 * FPS)))
    # toast 2s
    ranges += list(range(int(11 * FPS), int(13 * FPS)))
    # paste 1.5s
    ranges += list(range(int(14 * FPS), int(15.5 * FPS)))
    # end 1s
    ranges += list(range(int(17 * FPS), int(18 * FPS)))

    # downsample to ~12 fps and scale to 720 wide
    gif_idx = 0
    for fi in ranges[::2]:  # every other frame -> 12fps from 24
        fi = min(fi, total_frames - 1)
        src = Image.open(FRAMES / f"frame_{fi:05d}.png")
        src = src.resize((720, 405), Image.Resampling.LANCZOS)
        src.save(gif_frames_dir / f"g_{gif_idx:04d}.png")
        gif_idx += 1

    # palette + gif
    palette = "/tmp/whisper-demo-palette.png"
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "12",
        "-i", str(gif_frames_dir / "g_%04d.png"),
        "-vf", "palettegen=max_colors=128:stats_mode=diff",
        palette,
    ], check=True)
    subprocess.run([
        "ffmpeg", "-y", "-framerate", "12",
        "-i", str(gif_frames_dir / "g_%04d.png"),
        "-i", palette,
        "-lavfi", "paletteuse=dither=bayer:bayer_scale=3",
        "-loop", "0",
        str(gif),
    ], check=True)

    # if still too big, recompress
    size_mb = gif.stat().st_size / (1024 * 1024)
    print(f"GIF: {gif} ({size_mb:.2f} MB, {gif_idx} frames)")
    if size_mb > 8:
        print("GIF too large, recompressing at 640px...")
        gif_idx2 = 0
        gif_frames_dir2 = Path("/tmp/whisper-demo-gif2")
        if gif_frames_dir2.exists():
            shutil.rmtree(gif_frames_dir2)
        gif_frames_dir2.mkdir()
        for fi in ranges[::3]:
            fi = min(fi, total_frames - 1)
            src = Image.open(FRAMES / f"frame_{fi:05d}.png")
            src = src.resize((640, 360), Image.Resampling.LANCZOS)
            src.save(gif_frames_dir2 / f"g_{gif_idx2:04d}.png")
            gif_idx2 += 1
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "10",
            "-i", str(gif_frames_dir2 / "g_%04d.png"),
            "-vf", "palettegen=max_colors=96:stats_mode=diff",
            palette,
        ], check=True)
        subprocess.run([
            "ffmpeg", "-y", "-framerate", "10",
            "-i", str(gif_frames_dir2 / "g_%04d.png"),
            "-i", palette,
            "-lavfi", "paletteuse=dither=bayer:bayer_scale=4",
            "-loop", "0",
            str(gif),
        ], check=True)
        print(f"GIF recompressed: {gif.stat().st_size / (1024*1024):.2f} MB")


def main():
    total = render_all()
    assemble(total)
    for p in [DOCS / "demo.mp4", DOCS / "demo.gif", DOCS / "demo-poster.png"]:
        print(f"  {p.name}: {p.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
