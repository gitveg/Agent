#!/bin/bash

# 配置
APP_FILE="sanic_api.py"
LOG_DIR="./logs"
PID_FILE="./sanic.pid"
LOG_FILE="$LOG_DIR/sanic_api.log"

echo "开始启动Sanic服务..."

# 检查应用文件是否存在
if [ ! -f "$APP_FILE" ]; then
    echo "错误: $APP_FILE 不存在"
    exit 1
fi

# 创建日志目录
mkdir -p $LOG_DIR

# 检查是否已经在运行
if [ -f "$PID_FILE" ]; then
    pid=$(cat $PID_FILE)
    if ps -p $pid > /dev/null 2>&1; then
        echo "警告: Sanic服务已经在运行，PID: $pid"
        echo "如需重启，请先执行 ./stop_sanic.sh"
        exit 1
    else
        rm -f $PID_FILE
    fi
fi

# 启动Sanic应用
echo "启动Sanic服务..."
nohup python $APP_FILE > $LOG_FILE 2>&1 &

# 获取PID并保存
PID=$!
echo $PID > $PID_FILE
echo "Sanic服务已启动，PID: $PID"

# 等待几秒检查服务是否成功启动
sleep 2
if ps -p $PID > /dev/null; then
    echo "服务启动成功！"
    echo "日志文件: $LOG_FILE"
    echo "使用 './stop.sh' 停止服务"
else
    echo "错误: 服务启动失败！"
    echo "请检查日志文件: $LOG_FILE"
    cat $LOG_FILE
    exit 1
fi