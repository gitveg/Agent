#!/bin/bash

echo "正在启动Python多进程应用..."

# 记录开始时间
start_time=$(date +"%Y-%m-%d %H:%M:%S")
echo "启动时间: $start_time"

# 创建日志目录
log_dir="logs"
mkdir -p $log_dir
echo "已创建日志目录: $log_dir"

# 启动Python脚本并将PID保存到文件中
echo "正在启动主Python进程..."
python handle_file_server.py > $log_dir/app.log 2>&1 &
main_pid=$!
echo $main_pid > pid.txt
echo "主进程已启动，PID: $main_pid"

# 等待几秒确保进程正常启动
sleep 2

# 检查进程是否成功启动
if ps -p $main_pid > /dev/null; then
    echo "应用成功启动！"
    echo "日志文件位置: $log_dir/app.log"
    echo "可以使用 'tail -f $log_dir/app.log' 查看实时日志"
    echo "使用 './stop.sh' 停止应用"
else
    echo "错误：应用启动失败"
    exit 1
fi