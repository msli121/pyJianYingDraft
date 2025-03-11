#!/bin/bash

# 定义变量
CONDA_ENV_NAME="jianying"       # Conda 环境名称
DEFAULT_ENV="prod"              # 默认环境名称
PORT=7788                       # 运行端口

# 检查 conda 命令是否存在
if ! command -v conda &> /dev/null; then
    echo "Conda 没有找到。请先安装 Miniconda 或 Anaconda。"
    exit 1
fi

# 函数来创建和激活 conda 环境
setup_conda_env() {
    # 检查环境是否存在
    if conda info --envs | grep -q "^${CONDA_ENV_NAME}"; then
        echo "环境 '${CONDA_ENV_NAME}' 已经存在。"
    else
        echo "正在创建 '${CONDA_ENV_NAME}' 环境..."
        conda create --name ${CONDA_ENV_NAME} python=3.10 -y
    fi

    # 激活环境
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate ${CONDA_ENV_NAME}

    echo "Conda 环境 '${CONDA_ENV_NAME}' 已激活。"

    # 安装依赖包
    pip install -r requirements.txt

    echo "依赖包已安装"
}

# 函数来启动应用程序
start_app() {
    # 检查端口是否有进程运行
    PID=$(lsof -i :${PORT} -t)
    if [ ! -z "$PID" ]; then
        echo "A process is already running on port ${PORT}."
        exit 1
    fi

    local env=$1

    # 更新最新代码
    git pull

    # 指定环境类型，用于加载环境变量
    export FLASK_ENV=${.env}

    # 使用Gunicorn启动（推荐配置）
    gunicorn --workers 4 \
             --bind 0.0.0.0:${PORT} \
             --timeout 600 \
             --preload \
             --daemon \
             --access-logfile - \
             --error-logfile - \
             --log-level info \
             run:app
    echo "应用后台运行成功... 环境为 ${.env}。检查 'log/app.log' 了解详情。"
}

# 函数来停止应用程序
stop_app() {
    PID=$(lsof -i :${PORT} -t)
    if [ -z "$PID" ]; then
        echo "No process is running on port ${PORT}."
        return 0
    fi
    kill -9 $PID  # 强制终止进程
    echo "Process running on port ${PORT} has been forcibly stopped."
}

# 应用程序状态
status() {
    # 查询端口的进程号
    PID=$(lsof -i :${PORT} -t)
    if [ -z "$PID" ]; then
        echo "No process is running on port ${PORT}."
    else
        echo "Process is running on port ${PORT}."
    fi
}

# 解析命令行参数
ACTION=$1
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        -.env)
            ENV=$2
            shift
            shift
            ;;
        -auto_task)
            AUTO_TASK=$2
            shift
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# 使用默认值，如果命令行参数没有指定
ENV=${ENV:-${DEFAULT_ENV}}           # 默认环境

case $ACTION in
    start)
        setup_conda_env
        start_app $ENV
        ;;
    stop)
        stop_app
        ;;
    status)
        status
        ;;
    restart)
        stop_app
        setup_conda_env
        start_app $ENV
        ;;
    *)
        echo "Usage: $0 {start|stop|restart} [-env environment] [-auto_task 0|1]"
        exit 1
        ;;
esac