#!/bin/bash
# 安全同步脚本 - 先检查，后同步

LOG_FILE="/opt/mysql-sync/logs/sync.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "==========================================" | tee -a $LOG_FILE
echo "[$TIMESTAMP] 🚀 开始安全同步流程" | tee -a $LOG_FILE
echo "==========================================" | tee -a $LOG_FILE

# 步骤1：执行数据保护检查
echo "[$TIMESTAMP] 1. 执行数据保护检查..." | tee -a $LOG_FILE
cd /opt/mysql-sync/scripts
python3 data_protection.py

# 检查返回值
if [ $? -ne 0 ]; then
    echo "[$TIMESTAMP] 🚨 数据保护检查失败！终止同步。" | tee -a $LOG_FILE
    exit 1
fi

# 步骤2：执行智能同步
echo "[$TIMESTAMP] 2. 数据保护通过，开始同步..." | tee -a $LOG_FILE
python3 smart_sync.py

echo "[$TIMESTAMP] ✅ 安全同步流程完成。" | tee -a $LOG_FILE
