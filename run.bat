@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ========================================
echo   WhisperTray 启动脚本
echo ========================================

where python >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 python，请先安装 Python 3.11+ 并勾选 Add to PATH
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 创建虚拟环境 .venv ...
    python -m venv .venv
    if errorlevel 1 (
        echo [错误] 创建 venv 失败
        pause
        exit /b 1
    )
) else (
    echo [1/3] 虚拟环境已存在
)

echo [2/3] 安装/更新依赖 ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络或 Visual C++ 运行库
    pause
    exit /b 1
)

echo [3/3] 启动 WhisperTray ...
echo 提示: 首次运行会下载 Whisper 模型（small 约 500MB）
echo 关闭本窗口不会退出托盘（若已最小化）；右键托盘图标可退出
echo.
".venv\Scripts\python.exe" main.py
set EXITCODE=!ERRORLEVEL!
if not "!EXITCODE!"=="0" (
    echo.
    echo [错误] 程序退出码 !EXITCODE!，请查看日志目录
    pause
)
exit /b !EXITCODE!
