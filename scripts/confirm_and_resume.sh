#!/bin/bash
echo "=========================================="
echo "✅ 确认变更并恢复同步"
echo "=========================================="

echo ""
echo "1️⃣ 备份旧基线文件"
if [ -f /opt/mysql-sync/cache/baseline.json ]; then
    cp /opt/mysql-sync/cache/baseline.json /opt/mysql-sync/cache/baseline.json.backup.$(date +%Y%m%d_%H%M%S)
    echo "   ✅ 旧基线已备份"
fi

echo ""
echo "2️⃣ 创建新的数据基线（接受当前表结构）"
cd /opt/mysql-sync/scripts
python3 data_protection.py init

echo ""
echo "3️⃣ 移除暂停标记和告警缓存"
rm -f /opt/mysql-sync/PAUSE_SYNC
rm -f /opt/mysql-sync/cache/alerts.json
echo "   ✅ 同步已恢复"

echo ""
echo "4. 手动执行一次同步（补齐数据）"
python3 smart_sync.py

echo ""
echo "5. 最终状态检查"
bash /opt/mysql-sync/scripts/manage.sh status

echo ""
echo "=========================================="
echo "🎉 恢复完成！系统将使用新的表结构作为标准。"
echo "=========================================="
