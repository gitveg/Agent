#!/bin/bash

# 定义颜色输出
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
RESET="\033[0m"

# 记录开始时间
stop_time=$(date +"%Y-%m-%d %H:%M:%S")
echo -e "${BLUE}====================================================${RESET}"
echo -e "${BLUE}开始关闭项目所有服务 - $stop_time${RESET}"
echo -e "${BLUE}====================================================${RESET}"

# 定义服务列表及其目录（按照与启动相反的顺序关闭，确保依赖关系）
declare -A services
services["api_server"]="/home/zzh/Agent/src/server/api_server"
services["rerank_server"]="/home/zzh/Agent/src/server/rerank_server"
services["handle_file_server"]="/home/zzh/Agent/src/server/handle_file_server"
services["embedding_server"]="/home/zzh/Agent/src/server/embedding_server"

# 创建项目主日志目录
project_log_dir="./logs"
mkdir -p $project_log_dir
echo -e "${GREEN}已创建项目日志目录: $project_log_dir${RESET}"

# 创建关闭状态文件
status_file="$project_log_dir/shutdown_status.log"
echo "项目关闭状态 - $stop_time" > $status_file

# 关闭所有服务
for service_name in "${!services[@]}"; do
    service_dir=${services[$service_name]}
    
    echo -e "\n${YELLOW}正在关闭 $service_name...${RESET}"
    
    # 检查目录是否存在
    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}错误: 目录 $service_dir 不存在${RESET}"
        echo "$service_name - 失败 (目录不存在)" >> $status_file
        continue
    fi
    
    # 创建服务自己的日志目录
    service_log_dir="$service_dir/logs"
    mkdir -p $service_log_dir
    
    # 检查关闭脚本是否存在
    if [ ! -f "$service_dir/stop.sh" ]; then
        echo -e "${RED}错误: $service_dir/stop.sh 不存在${RESET}"
        echo "$service_name - 失败 (关闭脚本不存在)" >> $status_file
        continue
    fi
    
    # 执行关闭脚本并记录输出到服务自己的日志目录
    echo -e "${GREEN}执行: $service_dir/stop.sh${RESET}"
    cd $service_dir
    ./stop.sh > "$service_log_dir/${service_name}_stop.log" 2>&1
    stop_result=$?
    cd - > /dev/null
    
    # 检查关闭结果
    if [ $stop_result -eq 0 ]; then
        echo -e "${GREEN}$service_name 关闭成功!${RESET}"
        echo "$service_name - 成功" >> $status_file
        
        # 复制一份日志到项目主日志目录，以便集中查看
        cp "$service_log_dir/${service_name}_stop.log" "$project_log_dir/${service_name}_stop.log"
    else
        echo -e "${RED}$service_name 关闭失败! 退出代码: $stop_result${RESET}"
        echo -e "${YELLOW}查看日志: $service_log_dir/${service_name}_stop.log${RESET}"
        echo "$service_name - 失败 (退出代码: $stop_result)" >> $status_file
        
        # 复制一份日志到项目主日志目录，以便集中查看
        cp "$service_log_dir/${service_name}_stop.log" "$project_log_dir/${service_name}_stop.log"
    fi
    
    # 显示关闭日志前5行
    echo -e "${BLUE}$service_name 关闭日志摘要:${RESET}"
    head -n 5 "$service_log_dir/${service_name}_stop.log"
    echo "..."
done

# 检查是否有遗留进程
echo -e "\n${YELLOW}检查是否有遗留服务进程...${RESET}"
process_patterns=("api_server" "embedding_server" "handle_file_server" "rerank_server")
found_processes=false

for pattern in "${process_patterns[@]}"; do
    # 使用pgrep查找匹配的进程
    pids=$(pgrep -f "$pattern")
    if [ ! -z "$pids" ]; then
        found_processes=true
        echo -e "${RED}发现遗留 $pattern 进程: $pids${RESET}"
        echo "遗留 $pattern 进程: $pids" >> $status_file
        
        # 询问是否终止这些进程
        echo -e "${YELLOW}是否终止这些进程? (y/n)${RESET}"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            for pid in $pids; do
                echo -e "${RED}终止进程 PID: $pid${RESET}"
                kill -9 $pid 2>/dev/null
            done
            echo -e "${GREEN}已尝试终止所有遗留 $pattern 进程${RESET}"
            echo "尝试终止所有遗留 $pattern 进程" >> $status_file
        else
            echo -e "${YELLOW}保留遗留 $pattern 进程${RESET}"
            echo "保留遗留 $pattern 进程" >> $status_file
        fi
    fi
done

# 检查Python多进程模块创建的子进程
echo -e "\n${YELLOW}检查Python多进程子进程...${RESET}"
python_mp_pids=$(pgrep -f "multiprocessing.spawn" || pgrep -f "multiprocessing.resource_tracker")

if [ ! -z "$python_mp_pids" ]; then
    found_processes=true
    echo -e "${RED}发现Python多进程子进程: $python_mp_pids${RESET}"
    echo "Python多进程子进程: $python_mp_pids" >> $status_file
    
    # 询问是否终止这些进程
    echo -e "${YELLOW}是否终止这些多进程子进程? (y/n)${RESET}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        for pid in $python_mp_pids; do
            echo -e "${RED}终止多进程子进程 PID: $pid${RESET}"
            kill -9 $pid 2>/dev/null
        done
        echo -e "${GREEN}已尝试终止所有Python多进程子进程${RESET}"
        echo "尝试终止所有Python多进程子进程" >> $status_file
    else
        echo -e "${YELLOW}保留Python多进程子进程${RESET}"
        echo "保留Python多进程子进程" >> $status_file
    fi
fi

# 添加自动清理选项
if [ "$found_processes" = true ]; then
    echo -e "\n${YELLOW}是否要查找并清理所有Python相关进程? (y/n)${RESET}"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        echo -e "${RED}查找并终止所有Python相关进程...${RESET}"
        
        # 查找所有与项目可能相关的Python进程
        python_pids=$(ps aux | grep python | grep -v grep | grep -E 'qanything|Agent' | awk '{print $2}')
        
        if [ ! -z "$python_pids" ]; then
            echo -e "${RED}发现Python相关进程: $python_pids${RESET}"
            for pid in $python_pids; do
                echo -e "${RED}终止Python进程 PID: $pid${RESET}"
                kill -9 $pid 2>/dev/null
            done
            echo -e "${GREEN}已尝试终止所有相关Python进程${RESET}"
            echo "尝试终止所有相关Python进程" >> $status_file
        else
            echo -e "${GREEN}未找到其他Python相关进程${RESET}"
        fi
    fi
fi

if [ "$found_processes" = false ]; then
    echo -e "${GREEN}未发现遗留进程，关闭完成${RESET}"
    echo "未发现遗留进程" >> $status_file
fi

# 记录完成时间
end_time=$(date +"%Y-%m-%d %H:%M:%S")
echo -e "\n${BLUE}====================================================${RESET}"
echo -e "${BLUE}项目服务关闭完成 - $end_time${RESET}"
echo -e "${BLUE}====================================================${RESET}"
echo -e "${GREEN}项目主日志目录: $project_log_dir${RESET}"
echo -e "${GREEN}关闭状态文件: $status_file${RESET}\n"

# 将关闭状态添加到项目状态文件
echo "项目关闭完成 - $end_time" >> $status_file