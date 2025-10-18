#!/bin/bash

# 定义颜色输出
GREEN="\033[0;32m"
RED="\033[0;31m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
RESET="\033[0m"

# 记录开始时间
start_time=$(date +"%Y-%m-%d %H:%M:%S")
echo -e "${BLUE}====================================================${RESET}"
echo -e "${BLUE}开始启动项目所有服务 - $start_time${RESET}"
echo -e "${BLUE}====================================================${RESET}"

# 定义服务列表及其目录
declare -A services
services["embedding_server"]="/home/zzh/Agent/src/server/embedding_server"
services["handle_file_server"]="/home/zzh/Agent/src/server/handle_file_server"
services["rerank_server"]="/home/zzh/Agent/src/server/rerank_server"
services["api_server"]="/home/zzh/Agent/src/server/api_server"

# 创建项目主日志目录
project_log_dir="./logs"
mkdir -p $project_log_dir
echo -e "${GREEN}已创建项目日志目录: $project_log_dir${RESET}"

# 创建启动状态文件
status_file="$project_log_dir/startup_status.log"
echo "项目启动状态 - $start_time" > $status_file

# 启动所有服务
for service_name in "${!services[@]}"; do
    service_dir=${services[$service_name]}
    
    echo -e "\n${YELLOW}正在启动 $service_name...${RESET}"
    
    # 检查目录是否存在
    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}错误: 目录 $service_dir 不存在${RESET}"
        echo "$service_name - 失败 (目录不存在)" >> $status_file
        continue
    fi
    
    # 创建服务自己的日志目录
    service_log_dir="$service_dir/logs"
    mkdir -p $service_log_dir
    echo -e "${GREEN}已创建服务日志目录: $service_log_dir${RESET}"
    
    # 检查启动脚本是否存在
    if [ ! -f "$service_dir/start.sh" ]; then
        echo -e "${RED}错误: $service_dir/start.sh 不存在${RESET}"
        echo "$service_name - 失败 (启动脚本不存在)" >> $status_file
        continue
    fi
    
    # 执行启动脚本并记录输出到服务自己的日志目录
    echo -e "${GREEN}执行: $service_dir/start.sh${RESET}"
    cd $service_dir
    ./start.sh > "$service_log_dir/${service_name}_start.log" 2>&1
    start_result=$?
    cd - > /dev/null
    
    # 检查启动结果
    if [ $start_result -eq 0 ]; then
        echo -e "${GREEN}$service_name 启动成功!${RESET}"
        echo "$service_name - 成功" >> $status_file
        
        # 复制一份日志到项目主日志目录，以便集中查看
        cp "$service_log_dir/${service_name}_start.log" "$project_log_dir/${service_name}_start.log"
    else
        echo -e "${RED}$service_name 启动失败! 退出代码: $start_result${RESET}"
        echo -e "${YELLOW}查看日志: $service_log_dir/${service_name}_start.log${RESET}"
        echo "$service_name - 失败 (退出代码: $start_result)" >> $status_file
        
        # 复制一份日志到项目主日志目录，以便集中查看
        cp "$service_log_dir/${service_name}_start.log" "$project_log_dir/${service_name}_start.log"
    fi
    
    # 显示启动日志前5行
    echo -e "${BLUE}$service_name 启动日志摘要:${RESET}"
    head -n 5 "$service_log_dir/${service_name}_start.log"
    echo "..."
done

# 记录完成时间
end_time=$(date +"%Y-%m-%d %H:%M:%S")
echo -e "\n${BLUE}====================================================${RESET}"
echo -e "${BLUE}项目服务启动完成 - $end_time${RESET}"
echo -e "${BLUE}====================================================${RESET}"
echo -e "${GREEN}项目主日志目录: $project_log_dir${RESET}"
echo -e "${GREEN}启动状态文件: $status_file${RESET}"
echo -e "${YELLOW}使用 ./stop.sh 可停止所有服务${RESET}\n"

# 将启动状态添加到项目状态文件
echo "项目启动完成 - $end_time" >> $status_file