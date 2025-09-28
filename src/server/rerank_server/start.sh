#!/bin/bash
# Rerank 服务启动脚本

echo "Starting Rerank service..."

# 检查是否已经有rerank服务在运行
if lsof -i :8001 > /dev/null 2>&1; then
    echo "Warning: Port 8001 is already in use"
    echo "Current processes using port 8001:"
    lsof -i :8001
    echo "Please stop the existing service first using ./stop.sh"
    exit 1
fi

# 检查rerank_server.py是否存在
if [ ! -f "rerank_server.py" ]; then
    echo "Error: rerank_server.py not found in current directory"
    exit 1
fi

# 启动rerank服务
echo "Starting rerank server with nohup..."
nohup python rerank_server.py > record.log 2>&1 &

# 获取后台进程的PID
RERANK_PID=$!
echo "Rerank service started with PID: $RERANK_PID"

# 将PID保存到文件中，方便后续管理
echo $RERANK_PID > rerank.pid
echo "PID saved to rerank.pid file"

# 等待几秒钟让服务启动
echo "Waiting for service to start..."
sleep 20

# 检查端口并更新PID文件
PORT_PID=$(lsof -ti :8001)
if [ ! -z "$PORT_PID" ]; then
    echo $PORT_PID > embedding.pid
    echo "✓ Embedding service started successfully"
    echo "✓ Service is running on port 9001 (PID: $PORT_PID)"
    echo "✓ Log file: record.log"
    echo "✓ PID file: embedding.pid"
else
    echo "✗ Failed to start embedding service"
    echo "Check the log file for errors: record.log"
    exit 1
fi


echo "Rerank service startup completed"