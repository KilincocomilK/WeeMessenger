@echo off
cd /d "%~dp0"

:: ================================================
::  WeeMessenger 一键启动脚本
:: ================================================

echo.
echo  =============================================
echo    欢迎使用小信使！=w=
echo.
echo    初次使用前，请先打开微信客户端，使用快捷键
echo    Ctrl+F，手动搜索需要部署的群聊名并进入几次，
echo    确保群聊出现在搜索候选栏的首位，避免受到
echo    "搜索网络结果"的影响~
echo  =============================================
echo.

:: -- 如果有命令行参数，直接跳转启动 --
if not "%~1"=="" (
    goto :launch
)

:: -- 否则显示交互菜单 --
echo  =============================================
echo    WeeMessenger 启动菜单
echo  =============================================
echo.
echo    [1] 正常模式 - 连接 WebSocket 全天候运行
echo    [2] 调试模式 - 控制台发送消息到文件传输助手
echo.
echo  =============================================
echo.

set /p choice=请输入模式编号 (1 或 2):

if "%choice%"=="1" (
    echo.
    echo 已选择：正常模式
    goto :launch
)

if "%choice%"=="2" (
    echo.
    echo 已选择：调试模式
    set EXTRA_ARGS=--debug
    goto :launch
)

echo 无效选择，请输入 1 或 2
pause
exit /b 1

:: ================================================
::  启动逻辑
:: ================================================
:launch

:: 1. 创建虚拟环境（如不存在）
if not exist "venv\Scripts\python.exe" (
    echo [启动] 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo [错误] 创建虚拟环境失败，请检查 Python 是否已安装并加入 PATH
        pause
        exit /b 1
    )
    echo [启动] 虚拟环境创建完成
)

:: 2. 激活虚拟环境
call venv\Scripts\activate.bat

:: 3. 安装/验证依赖
echo [启动] 检查依赖...
pip install -r requirements.txt -q
if errorlevel 1 (
    echo [错误] 依赖安装失败
    pause
    exit /b 1
)

:: 4. 启动程序
echo [启动] 启动 WeeMessenger...
python main.py %* %EXTRA_ARGS%

:: 5. 暂停以便查看输出
pause
