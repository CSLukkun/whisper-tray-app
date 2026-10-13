# WhisperTray — 本地语音识别托盘工具

**版本：0.1.2**（见 `VERSION`）

在系统托盘 / 菜单栏常驻：点击开始/停止录音，本地 Whisper 转写后自动复制到剪贴板。适合日常「说一句 → 粘贴」场景。

支持 **Windows** 与 **macOS**（Apple Silicon / Intel）。

## 功能

- 系统托盘 / 菜单栏图标：点击切换录音；右键（macOS 可 Control+点击）菜单完整操作
- 本地 `faster-whisper` 识别（模型启动时加载并保持热态）
- 转写结果自动复制到剪贴板
- 可选桌面通知 / 提示音
- 中文友好默认（模型 `small`，语言 `zh`）
- 配置与录音保存在本机用户目录（见下方「数据与配置目录」）

## 环境要求

| 平台 | 要求 |
|------|------|
| **Windows 10/11** | Python 3.11+；麦克风权限；（可选）VC++ Redistributable、CUDA |
| **macOS 12+** | Python 3.11+（Apple Silicon 或 Intel）；**PortAudio**（`brew install portaudio`）；麦克风权限 |
| 通用 | （可选）NVIDIA GPU + CUDA 加速；无 GPU 时自动 CPU + int8。macOS 上一般为 CPU。 |
| ffmpeg | **一般不需要**：本工具录制并转写 WAV，`faster-whisper` 直接读 WAV 即可 |

## 快速开始

### macOS（推荐：`./run.sh`）

```bash
# 0) 若尚未安装 Homebrew / Python / PortAudio：
#    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
brew install python@3.12 portaudio

# 1) 克隆并启动
git clone https://github.com/CSLukkun/whisper-tray-app.git
cd whisper-tray-app
chmod +x run.sh
./run.sh
```

`run.sh` 会：创建 `.venv` → `pip install -r requirements.txt` → 启动 `main.py`。

**手动步骤（等价）：**

```bash
cd /path/to/whisper-tray-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

首次启动会下载 Whisper 模型（默认 `small`，约 **244–500MB**）。菜单栏图标出现后，标题显示「加载中…」，完成后变为「空闲 / 点击录音」。

#### macOS 麦克风权限（必做）

1. 打开 **系统设置 → 隐私与安全性 → 麦克风**
2. 允许运行本程序的宿主访问麦克风：
   - 用 `./run.sh` / 终端启动 → 勾选 **终端**（Terminal）或 **iTerm** 等
   - 用 VS Code / Cursor 集成终端启动 → 勾选对应编辑器
   - 若使用打包的 `WhisperTray.app` → 勾选 **WhisperTray**
3. 若列表中没有对应项：先点一次托盘「开始录音」，系统应弹出授权对话框；若仍无声音，检查输入设备是否为当前麦克风且未静音
4. 改权限后需**完全退出并重启** WhisperTray（菜单栏图标 → 退出）后再试

#### macOS 菜单栏使用提示

- 图标在屏幕**右上角**菜单栏（不是 Dock）
- 左键：开始/停止录音（默认菜单项）
- 右键或 **Control+点击**：打开完整菜单（模型、语言、打开日志等）
- macOS 会对菜单栏图标做 template 渲染，本应用用**形状**区分状态（圆环=空闲、录制样式=录音中、三点=忙碌、对勾=完成）

### Windows

#### 方式一：一键脚本（推荐）

双击 `run.bat`。脚本会：

1. 若不存在则创建 `.venv` 虚拟环境  
2. `pip install -r requirements.txt`  
3. 启动 `main.py`

#### 方式二：手动

```bat
cd /d 路径\whisper-tray-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## 使用说明

| 操作 | 说明 |
|------|------|
| 点击托盘 / 菜单栏图标 | 开始录音 ↔ 停止并识别 |
| 录音中 | 图标变为录音样式，标题「录音中…」 |
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

设备策略：有 CUDA 用 `float16`，否则 CPU `int8`（含 Apple Silicon）。

## 数据与配置目录

| 平台 | 路径 |
|------|------|
| Windows | `%LOCALAPPDATA%\WhisperTray\` |
| macOS | `~/Library/Application Support/WhisperTray/` |
| Linux / 其它 | `~/.whisper-tray/` |

目录内容：

```
config.json          # 模型、语言等
recordings/          # 录音 WAV
logs/                # 日志
last_transcript.txt  # 最近一次转写结果
```

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

## 开机自启

### Windows

1. `Win + R` → 输入 `shell:startup` → 回车  
2. 在启动文件夹中新建快捷方式，指向 `run.bat` 或打包后的 `WhisperTray.exe`  
3. 也可在「任务管理器 → 启动应用」中管理

### macOS

1. **系统设置 → 通用 → 登录项** →「打开时打开」→ 添加  
   - 源码方式：可添加一个「自动化」或使用登录时运行脚本；简便做法是把 `run.sh` 包进「应用程序」里的 Automator / 快捷指令，或直接添加打包好的 `WhisperTray.app`  
2. 推荐：安装 `WhisperTray.app`（从 `.dmg` 或 `./build_macos.sh`）后，将该 `.app` 加入登录项

## 免 Python 的可执行包

### Windows：从 Releases 下载

1. 打开仓库 **Releases**  
2. 下载 `WhisperTray-windows.zip`  
3. 解压后运行 `WhisperTray\WhisperTray.exe`  
4. 首次仍会下载 Whisper 模型；日志在 `%LOCALAPPDATA%\WhisperTray\logs\`

本机打包：双击或运行 `build_windows.bat`（须在 **Windows** 上）。

### macOS：下载 `.dmg` 或本机打包

#### 方式一：从 Releases 下载（推荐）

1. 打开仓库 [Releases](https://github.com/CSLukkun/whisper-tray-app/releases)
2. 下载 `WhisperTray-<version>-macos-arm64.dmg`（当前 CI 为 **Apple Silicon / arm64**，由 `macos-14` runner 构建）
3. 双击打开 `.dmg`，将 **WhisperTray.app** 拖到 **Applications**
4. 首次启动（**未签名 / 未公证**，Gatekeeper 会拦截）：
   - 在「应用程序」中 **右键** WhisperTray → **打开** → 仍要打开  
   - 或：系统设置 → 隐私与安全性 → 仍允许打开
5. 麦克风：系统设置 → 隐私与安全性 → 麦克风 → 勾选 **WhisperTray**；改权限后需完全退出再开
6. 首次运行仍会下载 Whisper 模型（不在包内）

也可用同 Release 里的 `WhisperTray-macos.zip`（解压得 `.app`），效果与 `.dmg` 相同。

#### 方式二：本机打包（需 macOS）

**无法在 Linux 上交叉编译出可用的 macOS `.app` / `.dmg`**（需 Cocoa 链接与 `hdiutil`）。请在 Mac 上：

```bash
cd /path/to/whisper-tray-app
chmod +x build_macos.sh package_macos_dmg.sh
./build_macos.sh
```

`build_macos.sh` 会：PyInstaller → `WhisperTray.app` → 调用 `package_macos_dmg.sh`（内置 `hdiutil`，含 Applications 符号链接）→ 产出 `.dmg`。

输出示例：

```
dist/WhisperTray.app
dist/WhisperTray-0.1.2-macos-arm64.dmg   # 架构随本机：arm64 或 x86_64
```

若已有 `.app`，可单独执行：

```bash
./package_macos_dmg.sh dist/WhisperTray.app
```

说明：

- **未签名 / 未公证**：首次打开 → 右键 → **打开**；或到「隐私与安全性」允许
- 麦克风：确认 **WhisperTray** 已勾选
- 模型权重**不**打进包内
- Apple Silicon 与 Intel 请在**对应架构**上各自打包；GitHub Actions 当前仅产出 **arm64** `.dmg`
- Linux 开发机只能改脚本/CI，无法本地验证真实 `.dmg`

### CI（GitHub Actions）

| 工作流 | 触发 | 产物 |
|--------|------|------|
| `build-windows.yml` | `workflow_dispatch` / tag `v*` | artifact `WhisperTray-windows`；Release 附 `WhisperTray-windows.zip` |
| `build-macos.yml` | 同上 | artifact：`.app` + `.dmg`；Release 附 `WhisperTray-macos.zip` 与 `WhisperTray-<ver>-macos-arm64.dmg`（**未签名**） |

发布示例：

```bash
git tag v0.1.2
git push origin v0.1.2
```

## 故障排除

| 现象 | 处理 |
|------|------|
| 无法打开麦克风（macOS） | 系统设置 → 隐私与安全性 → 麦克风，允许终端 / 编辑器 / WhisperTray；重启应用 |
| 无法打开麦克风（Windows） | 设置 → 隐私 → 麦克风，允许桌面应用；检查默认录音设备 |
| `sounddevice` / PortAudio 报错（macOS） | `brew install portaudio`，然后 `pip install --force-reinstall sounddevice` |
| 托盘图标不显示（macOS） | 看菜单栏右上角；确认 `pystray`、`Pillow` 已装；部分刘海屏机型图标在「控制中心」一侧 |
| 托盘图标一团黑（旧版） | 0.1.1+ 在 macOS 使用形状区分状态；请更新后重试 |
| 识别极慢 | 换 `tiny`/`base`；关闭其它占 CPU 程序；Windows 可考虑 CUDA |
| 模型下载失败 | 检查网络；可配置 Hugging Face 镜像；清理不完整缓存后重试 |
| 剪贴板无内容 | 确认已装 `pyperclip`；macOS 应有 `pbcopy`；查看日志 |
| `DLL load failed`（Windows） | 安装 [VC++ Redistributable](https://learn.microsoft.com/zh-cn/cpp/windows/latest-supported-vc-redist) |
| 空录音 / 无语音 | 靠近麦克风、提高音量；确认未静音 |
| `.app` / `.dmg` 无法打开（macOS） | 右键 → 打开；或在「隐私与安全性」中仍允许；本仓库 CI 产物未做 Apple 公证 / 签名 |

日志路径见上方「数据与配置目录」下的 `logs/`。

## 项目结构

```
whisper-tray-app/
  main.py                 # 入口
  tray_app.py             # 托盘 / 菜单栏 UI 与主流程
  recorder.py             # 麦克风录音 → WAV
  transcriber.py          # faster-whisper 转写
  clipboard_util.py       # 剪贴板（含 pbcopy）
  config.py               # 配置与数据目录
  requirements.txt
  run.bat                 # Windows 一键启动
  run.sh                  # macOS / Linux 一键启动
  build_windows.bat       # Windows 打包 exe
  build_macos.sh          # macOS 本机打包 .app + .dmg
  package_macos_dmg.sh    # 将 .app 打成 .dmg（hdiutil）
  whisper_tray.spec       # PyInstaller Windows
  whisper_tray_macos.spec # PyInstaller macOS .app
  VERSION
  LICENSE                 # MIT
  .github/workflows/build-windows.yml
  .github/workflows/build-macos.yml
  README.md
```

## 许可与致谢

- 本项目以 **MIT** 许可发布（见 `LICENSE`）
- 语音识别基于 [faster-whisper](https://github.com/SYSTRAN/faster-whisper)（CTranslate2）
- 仅供个人学习与日常效率工具使用

---

作者场景：程序员日常语音输入 → 粘贴到 IDE / 聊天 / 文档。
