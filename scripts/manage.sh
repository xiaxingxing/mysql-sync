#!/bin/bash
# MySQL同步系统管理工具

case "$1" in
    status)
        echo "=========================================="
        echo "MySQL同步系统状态"
        echo "=========================================="
        echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
        echo ""
        
        echo "1️⃣ 主从复制状态："
        mysql -uroot -p'Middle@Server#2024Pass' -e "SHOW SLAVE STATUS\G" 2>/dev/null | grep -E "Slave_IO_Running|Slave_SQL_Running|Seconds_Behind_Master" | sed 's/^/   /'
        
        echo ""
        echo "2️⃣ 同步状态："
        if [ -f /opt/mysql-sync/PAUSE_SYNC ]; then
            echo "   ⚠️  已暂停"
            echo "   原因: $(cat /opt/mysql-sync/PAUSE_SYNC | grep reason | cut -d'"' -f4)"
        else
            echo "   ✅ 正常运行"
        fi
        
        echo ""
        echo "3️⃣ 定时任务："
        CRON_COUNT=$(crontab -l 2>/dev/null | grep -c smart_sync)
        echo "   已设置 $CRON_COUNT 个同步任务"
        
        echo ""
        echo "4️⃣ 最近同步："
        if [ -f /opt/mysql-sync/logs/sync.log ]; then
            LAST_SYNC=$(grep "智能同步" /opt/mysql-sync/logs/sync.log | tail -1 | cut -d'-' -f2-)
            echo "   $LAST_SYNC"
            LAST_RESULT=$(grep "成功:" /opt/mysql-sync/logs/sync.log | tail -1)
            echo "   $LAST_RESULT"
        else
            echo "   暂无日志"
        fi
        
        echo ""
        echo "5️⃣ 数据对比："
        MIDDLE=$(mysql -uroot -p'Middle@Server#2024Pass' bynewapi -N -e "SELECT COUNT(*) FROM quota_data;" 2>/dev/null)
        CLOUD=$(mysql -h 35.220.220.225 -uroot -p'cGd4mQmiAyps6zsmQy@' -D bf-bynewapi -N -e "SELECT COUNT(*) FROM quota_data;" 2>/dev/null)
        echo "   中间服务器: $MIDDLE 行"
        echo "   Cloud SQL: $CLOUD 行"
        DIFF=$((MIDDLE - CLOUD))
        if [ $DIFF -eq 0 ]; then
            echo "   ✅ 数据完全一致"
        else
            echo "   差异: $DIFF 行"
        fi
        
        echo ""
        echo "=========================================="
        ;;
    
    sync)
        echo "🔄 手动执行同步..."
        cd /opt/mysql-sync/scripts
        python3 smart_sync.py
        ;;
    
    check)
        echo "🛡️  执行数据保护检查..."
        cd /opt/mysql-sync/scripts
        python3 data_protection.py
        ;;
    
    verify)
        echo "🔍 验证数据一致性..."
        echo ""
        echo "主要表对比："
        for table in quota_data tokens abilities users tasks; do
            MIDDLE=$(mysql -uroot -p'Middle@Server#2024Pass' bynewapi -N -e "SELECT COUNT(*) FROM $table;" 2>/dev/null)
            CLOUD=$(mysql -h 35.220.220.225 -uroot -p'cGd4mQmiAyps6zsmQy@' -D bf-bynewapi -N -e "SELECT COUNT(*) FROM $table;" 2>/dev/null)
            printf "%-15s  中间: %8s  Cloud: %8s  差异: %5s\n" "$table" "$MIDDLE" "$CLOUD" "$((MIDDLE - CLOUD))"
        done
        ;;
    
    logs)
        LOG_TYPE="${2:-sync}"
        echo "📋 查看 ${LOG_TYPE} 日志（最近50行）："
        tail -50 /opt/mysql-sync/logs/${LOG_TYPE}.log 2>/dev/null || echo "日志文件不存在"
        ;;
    
    pause)
        echo "⏸️  暂停自动同步..."
        touch /opt/mysql-sync/PAUSE_SYNC
        echo '{"reason": "Manual pause", "timestamp": "'$(date -Iseconds)'"}' > /opt/mysql-sync/PAUSE_SYNC
        echo "✅ 已暂停"
        ;;
    
    resume)
        echo "▶️  恢复自动同步..."
        rm -f /opt/mysql-sync/PAUSE_SYNC
        rm -f /opt/mysql-sync/cache/alerts.json
        echo "✅ 已恢复"
        ;;
    
    baseline)
        echo "📸 创建新的数据基线..."
        cd /opt/mysql-sync/scripts
        python3 data_protection.py init
        ;;
    
    *)
        cat << 'EOFHELP'
========================================
MySQL同步系统管理工具
========================================

用法: manage.sh <命令> [参数]

命令列表：
  status        查看系统状态
  sync          手动执行同步
  check         执行数据保护检查
  verify        验证数据一致性
  logs [type]   查看日志（sync/protection/baseline）
  pause         暂停自动同步
  resume        恢复自动同步
  baseline      创建新的数据基线

示例：
  bash /opt/mysql-sync/scripts/manage.sh status
  bash /opt/mysql-sync/scripts/manage.sh sync
  bash /opt/mysql-sync/scripts/manage.sh verify
  bash /opt/mysql-sync/scripts/manage.sh logs sync

========================================
EOFHELP
        exit 1
        ;;
esac
