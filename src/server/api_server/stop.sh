#!/bin/bash

# 配置
PID_FILE="./sanic.pid"

echo "开始关闭Sanic服务..."

# 检查PID文件是否存在
if [ ! -f "$PID_FILE" ]; then
    echo "警告: PID文件不存在，服务可能未运行"
    
    # 检查是否有Sanic进程在运行
    SANIC_PIDS=$(pgrep -f "sanic_api.py")
    if [ ! -z "$SANIC_PIDS" ]; then
        echo "发现运行中的Sanic进程: $SANIC_PIDS"
        echo "正在终止这些进程..."
        
        for pid in $SANIC_PIDS; do
            kill -15 $pid
            sleep 1
            if ps -p $pid > /dev/null 2>&1; then
                echo "进程 $pid 未响应，正在强制终止..."
                kill -9 $pid
            fi
        done
        echo "所有Sanic进程已终止"
    else
        echo "未发现运行中的Sanic进程"
    fi
    
    exit 0
fi

# 读取PID
PID=$(cat $PID_FILE)
echo "找到Sanic服务进程，PID: $PID"

# 验证进程是否存在
if ! ps -p $PID > /dev/null; then
    echo "进程 $PID 不存在，可能已经停止"
    rm -f $PID_FILE
    echo "已删除PID文件"
    exit 0
fi

# 关闭主进程
echo "正在关闭主进程 $PID..."
kill -15 $PID

# 等待进程终止
echo "等待进程终止..."
TIMEOUT=10
while ps -p $PID > /dev/null && [ $TIMEOUT -gt 0 ]; do
    sleep 1
    TIMEOUT=$((TIMEOUT-1))
done

# 检查是否成功终止
if ps -p $PID > /dev/null; then
    echo "进程未在预期时间内终止，正在强制终止..."
    kill -9 $PID
    sleep 2
fi

# 删除PID文件
if [ -f "$PID_FILE" ]; then
    rm -f $PID_FILE
    echo "已删除PID文件"
fi

# 检查是否还有相关进程
REMAINING_PIDS=$(pgrep -f "sanic_api.py")
if [ ! -z "$REMAINING_PIDS" ]; then
    echo "警告: 仍有Sanic相关进程在运行: $REMAINING_PIDS"
    echo "正在终止这些进程..."
    
    for pid in $REMAINING_PIDS; do
        kill -9 $pid
    done
    echo "所有残留进程已终止"
fi

echo "Sanic服务已成功关闭"