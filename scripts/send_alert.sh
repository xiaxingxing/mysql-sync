#!/bin/bash
# 统一告警接口

MESSAGE="$1"
SEVERITY="${2:-INFO}"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

echo "[$TIMESTAMP] 发送告警: [$SEVERITY] $MESSAGE"

# 发送邮件告警
if [ -f /opt/mysql-sync/scripts/alert_email.py ]; then
    python3 /opt/mysql-sync/scripts/alert_email.py "$MESSAGE" "$SEVERITY" 2>&1 | tee -a /opt/mysql-sync/logs/alert_email.log
fi

# 记录本地日志
echo "[$TIMESTAMP] [$SEVERITY] $MESSAGE" >> /opt/mysql-sync/logs/alerts.log

# 如果是严重告警，额外记录
if [ "$SEVERITY" = "CRITICAL" ]; then
    echo "[$TIMESTAMP] CRITICAL ALERT: $MESSAGE" >> /opt/mysql-sync/logs/critical_alerts.log
fi
