#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能数据保护 - 白名单模式 - 防重复告警
"""

import pymysql
import json
import hashlib
from datetime import datetime
from pathlib import Path
import sys
import os
import subprocess

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv('/opt/mysql-sync/.env')

# 允许结构变更的表
ALLOWED_SCHEMA_CHANGE_TABLES = {'quota_data', 'tokens', 'users'}
# 关键表
CRITICAL_TABLES = {'redemptions', 'top_ups'}

def send_alert(message, severity='CRITICAL'):
    """发送邮件告警"""
    try:
        subprocess.run(
            ['python3', '/opt/mysql-sync/scripts/alert_email.py', message, severity],
            timeout=30, check=False
        )
        print("  📧 邮件告警已发送")
    except Exception as e:
        print(f"  ⚠️  邮件发送失败: {e}")

class SmartDataProtector:
    def __init__(self):
        self.cache_dir = Path('/opt/mysql-sync/cache')
        self.cache_dir.mkdir(exist_ok=True)
        self.baseline_file = self.cache_dir / 'baseline.json'
        self.alert_file = self.cache_dir / 'alerts.json'
        self.pause_file = Path('/opt/mysql-sync/PAUSE_SYNC') # 新增：暂停文件路径
        self.load_baseline()
        
    def connect_db(self, prefix='MIDDLE'):
        return pymysql.connect(
            host=os.getenv(f'{prefix}_HOST'),
            port=int(os.getenv(f'{prefix}_PORT', 3306)),
            user=os.getenv(f'{prefix}_USER'),
            password=os.getenv(f'{prefix}_PASS'),
            database=os.getenv(f'{prefix}_DB'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def load_baseline(self):
        if self.baseline_file.exists():
            with open(self.baseline_file, 'r') as f:
                self.baseline = json.load(f)
        else:
            self.baseline = {'table_schemas': {}, 'row_counts': {}}
    
    def save_baseline(self):
        self.baseline['last_update'] = datetime.now().isoformat()
        with open(self.baseline_file, 'w') as f:
            json.dump(self.baseline, f, indent=2)

    def create_baseline(self):
         # 添加暂停状态检查
        if self.pause_file.exists():
            print("🚫 系统处于暂停状态，拒绝创建新基线以防止掩盖数据问题。")
            print("💡 请先解决数据保护告警，系统自动恢复后再重新创建基线。")
            sys.exit(1)
        
        print("📸 创建数据基线快照...")
        conn = self.connect_db('MIDDLE')
        cursor = conn.cursor()
        cursor.execute("SHOW TABLES")
        tables = [list(row.values())[0] for row in cursor.fetchall()]
        for table in tables:
            if table.startswith('_'): continue
            try:
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                schema_hash = hashlib.md5(str(cursor.fetchone()).encode()).hexdigest()
                self.baseline['table_schemas'][table] = schema_hash
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                self.baseline['row_counts'][table] = cursor.fetchone()['cnt']
                print(f"  ✓ {table}: {self.baseline['row_counts'][table]:,} rows")
            except Exception as e: print(f"  ✗ {table}: {e}")
        cursor.close()
        conn.close()
        self.save_baseline()
        print("\n✅ 基线已保存")

    def check_delete_anomaly(self):
        print("\n🔍 检查数据删除异常...")
        conn = self.connect_db('MIDDLE')
        cursor = conn.cursor()
        alerts = []
        delete_threshold = float(os.getenv('DELETE_THRESHOLD_PERCENT', 10))
        for table, baseline_count in self.baseline.get('row_counts', {}).items():
            try:
                cursor.execute(f"SELECT COUNT(*) as cnt FROM `{table}`")
                current_count = cursor.fetchone()['cnt']
                if baseline_count > 0:
                    decrease_percent = ((baseline_count - current_count) / baseline_count) * 100
                    if decrease_percent > delete_threshold:
                        alerts.append({'type': 'MASSIVE_DELETE', 'severity': 'CRITICAL', 'table': table})
                        print(f"  🚨 {table}: {baseline_count:,} → {current_count:,} (-{decrease_percent:.1f}%)")
                    else:
                        print(f"  ✓ {table}: {current_count:,} rows")
            except Exception as e: print(f"  ⚠️  {table}: {e}")
        cursor.close()
        conn.close()
        return alerts

    def check_schema_change(self):
        print("\n🔍 检查表结构变更（智能模式）...")
        conn = self.connect_db('MIDDLE')
        cursor = conn.cursor()
        alerts = []
        try:
            cursor.execute("SHOW TABLES")
            current_tables = {list(row.values())[0] for row in cursor.fetchall()}
            baseline_tables = set(self.baseline.get('table_schemas', {}).keys())
            dropped_tables = baseline_tables - current_tables
            if dropped_tables:
                alerts.append({'type': 'TABLE_DROPPED', 'severity': 'CRITICAL', 'tables': list(dropped_tables)})
                print(f"  🚨 表被删除: {dropped_tables}")
            
            for table in current_tables:
                if table.startswith('_') or table not in baseline_tables: continue
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                current_hash = hashlib.md5(str(cursor.fetchone()).encode()).hexdigest()
                baseline_hash = self.baseline['table_schemas'][table]
                if current_hash != baseline_hash:
                    if table in ALLOWED_SCHEMA_CHANGE_TABLES:
                        print(f"  ℹ️  {table}: 结构已变更（允许，自动更新）")
                        self.baseline['table_schemas'][table] = current_hash
                    elif table in CRITICAL_TABLES:
                        alerts.append({'type': 'CRITICAL_TABLE_SCHEMA_CHANGED', 'severity': 'CRITICAL', 'table': table})
                        print(f"  🚨🚨 {table}: 关键表结构被修改！")
                    else:
                        alerts.append({'type': 'SCHEMA_CHANGED', 'severity': 'HIGH', 'table': table})
                        print(f"  🚨 {table}: 结构已变更")
                else:
                    print(f"  ✓ {table}: 结构正常")
        except Exception as e: print(f"  ⚠️  {e}")
        finally:
            cursor.close()
            conn.close()
        return alerts

    def run_full_check(self):
        print("="*70)
        print(f"🛡️  智能数据保护检查 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        all_alerts = self.check_delete_anomaly() + self.check_schema_change()
        critical_alerts = [a for a in all_alerts if a.get('severity') == 'CRITICAL']
        
        # 核心逻辑修改：如果已暂停，则不重复发送告警
        if self.pause_file.exists() and critical_alerts:
            print("🚫 系统已暂停，不再重复发送告警。")
            return False # 保持暂停状态

        if critical_alerts:
            print(f"\n🚨 发现 {len(critical_alerts)} 个严重问题，暂停同步并发送告警。")
            with open(self.pause_file, 'w') as f:
                report = {'reason': 'Critical data protection alert', 'alerts': critical_alerts}
                json.dump(report, f, indent=2)
            
            alert_msg = f"检测到 {len(critical_alerts)} 个严重问题，同步已暂停:\n"
            for alert in critical_alerts:
                alert_msg += f"- {alert['type']}: {alert.get('table', alert.get('tables', 'N/A'))}\n"
            
            send_alert(alert_msg, 'CRITICAL')
            return False
        else:
            print("\n✅ 所有检查通过")
            if self.pause_file.exists():
                self.pause_file.unlink() # 如果之前是暂停的，现在问题解决了就自动恢复
                send_alert("✅ 数据保护问题已解决，同步已自动恢复。", "INFO")
            self.save_baseline()
            return True

if __name__ == '__main__':
    protector = SmartDataProtector()
    if len(sys.argv) > 1 and sys.argv[1] == 'init':
        protector.create_baseline()
    else:
        result = protector.run_full_check()
        sys.exit(0 if result else 1)
