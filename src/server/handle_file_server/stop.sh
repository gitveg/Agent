#!/bin/bash

echo "正在停止Python多进程应用..."

# 检查PID文件是否存在
if [ ! -f "pid.txt" ]; then
    echo "错误：找不到pid.txt文件，应用可能未运行"
    exit 1
fi

# 读取主进程PID
main_pid=$(cat pid.txt)
echo "找到主进程PID: $main_pid"

# 检查主进程是否仍在运行
if ! ps -p $main_pid > /dev/null; then
    echo "警告：主进程 $main_pid 已不存在"
else
    echo "正在停止主进程 $main_pid..."
    
    # 获取所有子进程
    child_pids=$(pgrep -P $main_pid)
    if [ ! -z "$child_pids" ]; then
        echo "发现子进程: $child_pids"
        echo "正在停止所有子进程..."
        for pid in $child_pids; do
            echo "停止子进程 $pid..."
            kill -15 $pid
            sleep 1
            # 如果进程仍然存在，强制终止
            if ps -p $pid > /dev/null; then
                echo "子进程 $pid 未响应，正在强制终止..."
                kill -9 $pid
            fi
        done
    else
        echo "未发现子进程"
    fi
    
    # 停止主进程
    echo "正在停止主进程 $main_pid..."
    kill -15 $main_pid
    sleep 2
    
    # 检查主进程是否已停止，如果没有则强制终止
    if ps -p $main_pid > /dev/null; then
        echo "主进程未响应，正在强制终止..."
        kill -9 $main_pid
    fi
fi

# 记录停止时间
stop_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "应用已停止，停止时间: $stop_time"

# 删除PID文件
rm -f pid.txt
echo "已清理PID文件"

echo "应用已完全停止"