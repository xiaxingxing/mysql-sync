#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能同步引擎 - 增量同步到Cloud SQL
"""

import pymysql
import subprocess
import json
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv

load_dotenv('/opt/mysql-sync/.env')

class SmartSyncEngine:
    def __init__(self):
        self.cache_dir = Path('/opt/mysql-sync/cache')
        self.log_dir = Path('/opt/mysql-sync/logs')
        self.log_dir.mkdir(exist_ok=True)
        
        self.checksum_file = self.cache_dir / 'table_checksums.json'
        self.load_checksums()
    
    def load_checksums(self):
        """加载上次的表校验和"""
        if self.checksum_file.exists():
            with open(self.checksum_file, 'r') as f:
                self.last_checksums = json.load(f)
        else:
            self.last_checksums = {}
    
    def save_checksums(self):
        """保存校验和"""
        with open(self.checksum_file, 'w') as f:
            json.dump(self.last_checksums, f, indent=2)
    
    def connect_db(self, prefix='MIDDLE'):
        """连接数据库"""
        return pymysql.connect(
            host=os.getenv(f'{prefix}_HOST'),
            port=int(os.getenv(f'{prefix}_PORT', 3306)),
            user=os.getenv(f'{prefix}_USER'),
            password=os.getenv(f'{prefix}_PASS'),
            database=os.getenv(f'{prefix}_DB'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    def get_table_checksum(self, table):
        """获取表的校验和"""
        conn = self.connect_db('MIDDLE')
        cursor = conn.cursor()
        
        try:
            cursor.execute(f"CHECKSUM TABLE `{table}`")
            result = cursor.fetchone()
            checksum = result['Checksum']
        except Exception as e:
            print(f"  ⚠️  {table}: {e}")
            checksum = None
        finally:
            cursor.close()
            conn.close()
        
        return checksum
    
    def find_changed_tables(self):
        """找出变化的表"""
        print("🔍 扫描变化的表...")
        
        conn = self.connect_db('MIDDLE')
        cursor = conn.cursor()
        
        cursor.execute("SHOW TABLES")
        all_tables = [list(row.values())[0] for row in cursor.fetchall()]
        
        cursor.close()
        conn.close()
        
        changed_tables = []
        unchanged_count = 0
        
        for table in all_tables:
            if table.startswith('_'):
                continue
            
            current_checksum = self.get_table_checksum(table)
            last_checksum = self.last_checksums.get(table)
            
            if current_checksum != last_checksum:
                changed_tables.append(table)
                self.last_checksums[table] = current_checksum
                print(f"  ✓ {table} - 已变化")
            else:
                unchanged_count += 1
        
        print(f"  变化: {len(changed_tables)} 个, 未变化: {unchanged_count} 个")
        
        self.save_checksums()
        
        return changed_tables
    
    def sync_table(self, table):
        """同步单个表到Cloud SQL"""
        print(f"  同步表: {table} ", end='', flush=True)
        
        middle_db = os.getenv('MIDDLE_DB')
        cloud_host = os.getenv('CLOUD_HOST')
        cloud_user = os.getenv('CLOUD_USER')
        cloud_pass = os.getenv('CLOUD_PASS')
        cloud_db = os.getenv('CLOUD_DB')
        middle_pass = os.getenv('MIDDLE_PASS')
        
        dump_cmd = [
            'mysqldump',
            '-h', 'localhost',
            '-uroot',
            f'-p{middle_pass}',
            '--single-transaction',
            '--add-drop-table',
            # '--no-create-info',
            # '--skip-add-drop-table',
            '--replace',
            '--quick',
            '--lock-tables=false',
            middle_db,
            table
        ]
        
        import_cmd = [
            'mysql',
            '-h', cloud_host,
            f'-u{cloud_user}',
            f'-p{cloud_pass}',
            cloud_db
        ]
        
        try:
            dump_proc = subprocess.Popen(
                dump_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            import_proc = subprocess.Popen(
                import_cmd,
                stdin=dump_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            dump_proc.stdout.close()
            import_output, import_error = import_proc.communicate(timeout=300)
            
            if import_proc.returncode == 0:
                print("✅")
                return True
            else:
                error_msg = import_error.decode().strip()
                print(f"❌ {error_msg[:100]}")
                return False
                
        except subprocess.TimeoutExpired:
            dump_proc.kill()
            import_proc.kill()
            print("❌ 超时")
            return False
        except Exception as e:
            print(f"❌ {e}")
            return False
    
    def run(self):
        """执行同步"""
        pause_file = Path('/opt/mysql-sync/PAUSE_SYNC')
        if pause_file.exists():
            print("🚫 同步已暂停（数据保护告警）")
            print(f"   查看详情: cat {pause_file}")
            return False
        
        print("="*70)
        print(f"🔄 智能同步 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        changed_tables = self.find_changed_tables()
        
        if not changed_tables:
            print("\n✅ 没有表需要同步")
            return True
        
        print(f"\n🚀 开始同步 {len(changed_tables)} 个表到Cloud SQL...")
        
        success_count = 0
        for table in changed_tables:
            if self.sync_table(table):
                success_count += 1
        
        print(f"\n{'='*70}")
        print(f"✅ 成功: {success_count}/{len(changed_tables)}")
        print("="*70)
        
        return success_count == len(changed_tables)

if __name__ == '__main__':
    engine = SmartSyncEngine()
    result = engine.run()
    sys.exit(0 if result else 1)
