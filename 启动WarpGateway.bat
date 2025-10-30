@echo off
chcp 65001 >nul
title WarpGateway

echo 正在启动 WarpGateway...
echo.

cd /d "%~dp0"

if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
    python run_gui.py
) else (
    echo 错误: 未找到虚拟环境，请先运行 pip install -e .
    pause
)
