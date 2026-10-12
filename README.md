# WhisperTray — 本地语音识别托盘工具

**版本：0.1.0**（见 `VERSION`）

在 Windows 系统托盘常驻：点击开始/停止录音，本地 Whisper 转写后自动复制到剪贴板。适合日常「说一句 → 粘贴」场景。

## 演示

![WhisperTray 使用演示](docs/demo.gif)

<video src="docs/demo.mp4" controls width="720" poster="docs/demo-poster.png"></video>

[观看 MP4 演示视频](docs/demo.mp4)

## 功能

- 系统托盘图标：左键切换录音；右键菜单完整操作
- 本地 `faster-whisper` 识别（模型启动时加载并保持热态）
- 转写结果自动复制到剪贴板
- 可选桌面通知 / 提示音
- 中文友好默认（模型 `small`，语言 `zh`）
- 配置与录音保存在 `%LOCALAPPDATA%\WhisperTray\`

## 环境要求

- **Windows 10/11**（主要目标平台）
- **Python 3.11+**（推荐 3.11 / 3.12）
- 麦克风权限
- （可选）NVIDIA GPU + CUDA：加速识别；无 GPU 时自动用 CPU + int8
- （可选）[Microsoft Visual C++ Redistributable](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist) — 部分原生依赖需要
- **一般不需要 ffmpeg**：本工具录制并转写 WAV，`faster-whisper` 直接读 WAV 即可

## 快速开始

### 方式一：一键脚本（推荐）

双击 `run.bat`。脚本会：

1. 若不存在则创建 `.venv` 虚拟环境  
2. `pip install -r requirements.txt`  
3. 启动 `main.py`

### 方式二：手动

```bat
cd /d 路径\whisper-tray-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

首次启动会下载 Whisper 模型（默认 `small`，约 **244–500MB** 量级，视缓存与量化而定）。托盘标题显示「加载中…」，完成后变为「空闲 / 点击录音」。

## 使用说明

| 操作 | 说明 |
|------|------|
| 左键点击托盘图标 | 开始录音 ↔ 停止并识别 |
| 录音中 | 图标变红，标题「录音中…」 |
| 停止后 | 标题「识别中…」→ 复制剪贴板 →「已复制」 |
| 右键 → 选择模型 | tiny / base / small / medium |
| 右键 → 选择语言 | 自动检测 / 中文 / 英语 |
| 右键 → 打开日志目录 | 查看运行日志 |
| 右键 → 退出 | 退出程序 |

### 模型建议

| 模型 | 体积/内存 | 速度 | 准确度 | 建议场景 |
|------|-----------|------|--------|----------|
| tiny | 最小 | 最快 | 一般 | 试玩 / 低配 |
| base | 小 | 快 | 尚可 | 轻量日常 |
| **small** | 中 | 中 | **较好** | **默认推荐** |
| medium | 较大 | 较慢 | 更好 | 高配 / 追求准确 |

设备策略：有 CUDA 用 `float16`，否则 CPU `int8`。

## 数据与配置目录

Windows：

```
%LOCALAPPDATA%\WhisperTray\
  config.json          # 模型、语言等
  recordings\          # 录音 WAV
  logs\                # 日志
  last_transcript.txt  # 最近一次转写结果
```

非 Windows（便于开发测试）：`~/.whisper-tray/`

`config.json` 示例：

```json
{
  "model": "small",
  "language": "zh",
  "device": "auto",
  "compute_type": "auto",
  "hotkey": null,
  "sample_rate": 16000,
  "channels": 1,
  "beam_size": 5,
  "vad_filter": true,
  "notify": true
}
```

`hotkey` 字段预留，后续可扩展全局热键。

## 开机自启（Windows）

1. `Win + R` → 输入 `shell:startup` → 回车  
2. 在启动文件夹中新建 `WhisperTray` 的快捷方式，目标指向：

   ```
   D:\path\to\whisper-tray-app\run.bat
   ```

   若使用打包版，快捷方式直接指向：

   ```
   D:\path\to\WhisperTray\WhisperTray.exe
   ```

   或（源码 + venv）直接指向：

   ```
   D:\path\to\whisper-tray-app\.venv\Scripts\pythonw.exe
   ```

   参数：`D:\path\to\whisper-tray-app\main.py`  
   （`pythonw.exe` 无控制台窗口，更适合托盘常驻）

3. 也可在「任务管理器 → 启动应用」中管理启用/禁用

## 免 Python 的 .exe

无需安装 Python 即可使用：从 GitHub Releases 下载预编译包，或在本机用脚本打包。

### 从 Releases 下载（推荐给最终用户）

1. 打开仓库的 **Releases** 页面  
2. 下载最新的 `WhisperTray-windows.zip`（由 CI 在打标签时自动上传）  
3. 解压到任意目录，运行 `WhisperTray\WhisperTray.exe`  
4. 首次运行仍会下载 Whisper 模型到 Hugging Face 缓存（与源码方式相同）  
5. 日志：`%LOCALAPPDATA%\WhisperTray\logs\`（窗口模式无控制台，请看文件日志）  
6. 若提示缺少 DLL，安装 [VC++ Redistributable](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist)

也可在 Actions 产物中下载 artifact `WhisperTray-windows`（`workflow_dispatch` 或打 tag 触发构建后）。

### 本机打包：`build_windows.bat`

在 **Windows** 上双击或在 cmd 中运行：

```bat
cd /d 路径\whisper-tray-app
build_windows.bat
```

脚本会：创建 `.venv`（若不存在）→ 安装 `requirements.txt` + `pyinstaller` → 执行 `pyinstaller whisper_tray.spec`。

完成后输出：

```
dist\WhisperTray\          ← 整个文件夹一起分发（one-folder）
dist\WhisperTray\WhisperTray.exe
```

也可手动：

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt pyinstaller
pyinstaller whisper_tray.spec
```

说明：

- **one-folder**（默认）：启动更快，适合 `faster-whisper` / `ctranslate2` / `onnxruntime` 等大量原生 DLL  
- 模型权重**不**打进 exe；首次运行仍可能下载  
- 请在 Windows 上打包（Linux 交叉编译 Windows exe 一般不可行）  
- `whisper_tray.spec` 已用 `collect_all` 收集常见依赖；`console=False`（托盘无黑窗），调试时可临时改 `True`

### CI 自动构建（GitHub Actions）

工作流：`.github/workflows/build-windows.yml`

| 触发 | 行为 |
|------|------|
| `workflow_dispatch`（手动） | 在 `windows-latest` 上构建，上传 artifact `WhisperTray-windows` |
| 推送标签 `v*`（如 `v0.1.0`） | 同上，并创建 GitHub Release，附加 `WhisperTray-windows.zip` |

发布示例：

```bat
git tag v0.1.0
git push origin v0.1.0
```

（需已配置仓库权限；本仓库本地改动后请自行 push / 打 tag，助手不会代为推送。）

## 故障排除

| 现象 | 处理 |
|------|------|
| 无法打开麦克风 | 系统设置 → 隐私 → 麦克风，允许桌面应用访问；检查默认录音设备 |
| 托盘图标不显示 | 确认已安装 `pystray`、`Pillow`；部分环境需托盘溢出区显示 |
| 识别极慢 | 换 `tiny`/`base`，或安装 CUDA 版驱动；关闭其它占 CPU 程序 |
| 模型下载失败 | 检查网络；可配置 Hugging Face 镜像；清理不完整缓存后重试 |
| 剪贴板无内容 | 确认已装 `pyperclip`；或看日志是否「识别结果为空」 |
| `DLL load failed` | 安装最新 [VC++ Redistributable](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist) |
| 空录音 / 无语音 | 靠近麦克风、提高音量；确认未静音 |

日志路径：`%LOCALAPPDATA%\WhisperTray\logs\`

## 项目结构

```
whisper-tray-app/
  main.py              # 入口
  tray_app.py          # 托盘 UI 与主流程
  recorder.py          # 麦克风录音 → WAV
  transcriber.py       # faster-whisper 转写
  clipboard_util.py    # 剪贴板
  config.py            # 配置与数据目录
  requirements.txt
  run.bat              # Windows 一键启动（需 Python）
  build_windows.bat    # Windows 打包为 exe
  whisper_tray.spec    # PyInstaller one-folder 规格
  VERSION              # 当前版本号
  LICENSE              # MIT
  .github/workflows/build-windows.yml
  README.md
```

## 许可与致谢

- 本项目以 **MIT** 许可发布（见 `LICENSE`）
- 语音识别基于 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2）
- 仅供个人学习与日常效率工具使用

---

作者场景：程序员日常语音输入 → 粘贴到 IDE / 聊天 / 文档。
