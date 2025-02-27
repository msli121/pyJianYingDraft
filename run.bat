@echo off
REM 强制命令行使用 UTF-8 编码
chcp 65001

REM 定义变量
set "CONDA_ENV_NAME=jianying"
set "DEFAULT_ENV=prod"
set "PORT=7788"
set "PYTHON_SCRIPT=run.py"        REM 要运行的 Python 脚本


REM 主入口
call :main %*
exit /b %errorlevel%

:main
if "%1"=="" (
    echo Usage: %~n0 {start^|stop^|restart^|status} [-env environment] [-auto_task 0^|1]
    exit /b 1
)

set "ACTION=%1"
shift

REM 解析参数
:parse_args
if "%1"=="" goto args_done
if "%1"=="-env" (
    set "ENV=%2"
    shift
    shift
    goto parse_args
)
shift
goto parse_args

:args_done
set "ENV=%ENV%"
if "%ENV%"=="" set "ENV=%DEFAULT_ENV%"

REM 分发操作
if /i "%ACTION%"=="start" (
    call :setup_conda_env
    call :start_app "%ENV%"
) else if /i "%ACTION%"=="stop" (
    call :stop_app
) else if /i "%ACTION%"=="status" (
    call :status
) else if /i "%ACTION%"=="restart" (
    call :stop_app
    call :setup_conda_env
    call :start_app "%ENV%"
) else (
    echo Invalid action: %ACTION%
    exit /b 1
)
exit /b 0

REM 创建和激活 conda 环境
:setup_conda_env
conda info --envs | findstr /b /c:"%CONDA_ENV_NAME% " >nul 2>&1
if %errorlevel% == 0 (
    echo Environment "%CONDA_ENV_NAME%" already exists.
) else (
    echo Creating "%CONDA_ENV_NAME%" environment...
    conda create --name %CONDA_ENV_NAME% python=3.10 -y
)

call conda activate %CONDA_ENV_NAME%
if %errorlevel% neq 0 (
    echo Failed to activate conda environment
    exit /b 1
)
echo Conda environment "%CONDA_ENV_NAME%" activated.

pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
if %errorlevel% neq 0 (
    echo 安装依赖失败
    pause
    exit /b 1
)
echo 依赖已安装
exit /b 0

REM 启动应用程序
:start_app
echo Pulling latest code...
git pull

set "FLASK_ENV=%~1"

echo Starting application on port %PORT%...
python %PYTHON_SCRIPT%
echo Application started in %FLASK_ENV% environment
exit /b 0

REM 停止应用程序
:stop_app
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":%PORT%"') do set PID=%%a
if "%PID%"=="" (
    echo No process found on port %PORT%
    exit /b 0
)

taskkill /F /PID %PID% >nul 2>&1
if %errorlevel% == 0 (
    echo Process %PID% killed
) else (
    echo Failed to kill process on port %PORT%
)
exit /b 0

REM 查看状态
:status
netstat -ano | findstr ":%PORT%" >nul
if %errorlevel% == 0 (
    echo Process is running on port %PORT%
) else (
    echo No process found on port %PORT%
)
exit /b 0
