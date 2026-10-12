@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo   WhisperTray — Windows 打包 (PyInstaller)
echo ========================================
echo.

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.11+ / 3.12 并勾选 Add to PATH
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] 创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建 venv 失败
        pause
        exit /b 1
    )
) else (
    echo [1/4] 虚拟环境已存在
)

echo [2/4] 安装依赖 + PyInstaller ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

echo [3/4] 清理旧的 build/ dist/WhisperTray ...
if exist "build" rmdir /s /q "build"
if exist "dist\WhisperTray" rmdir /s /q "dist\WhisperTray"

echo [4/4] 运行 pyinstaller whisper_tray.spec ...
".venv\Scripts\pyinstaller.exe" whisper_tray.spec
if errorlevel 1 (
    echo [错误] PyInstaller 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo   打包完成
echo ========================================
echo 输出目录: %CD%\dist\WhisperTray\
echo 可执行文件: %CD%\dist\WhisperTray\WhisperTray.exe
echo.
echo 分发时请打包整个 dist\WhisperTray\ 文件夹（one-folder 模式）。
echo 日志仍写入: %%LOCALAPPDATA%%\WhisperTray\logs\
echo 首次运行仍会下载 Whisper 模型到 Hugging Face 缓存。
echo.
pause
exit /b 0
