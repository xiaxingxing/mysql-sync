#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件告警通知系统
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import sys

# ============================================
# 邮箱配置（请修改为你的信息）
# ============================================

# 使用QQ邮箱（推荐）
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 587

# 发件邮箱（你的QQ邮箱）
SENDER_EMAIL = "1657703775@qq.com"

# QQ邮箱授权码（不是QQ密码！是16位授权码）
SENDER_PASSWORD = "kdamvydlotdlcgdb"

# 收件邮箱（可以和发件邮箱相同）
RECEIVER_EMAIL = "1657703775@qq.com"

# ============================================

def send_email(subject, message, severity='INFO'):
    """发送邮件告警"""
    
    color_map = {
        'INFO': '#4444ff',
        'WARNING': '#ffaa00',
        'HIGH': '#ff6600',
        'CRITICAL': '#ff0000'
    }
    
    bg_color = color_map.get(severity, '#4444ff')
    
    msg = MIMEMultipart('alternative')
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = f"[{severity}] MySQL同步告警 - {subject}"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="UTF-8">
        <style>
          body {{ font-family: Arial, sans-serif; line-height: 1.6; }}
          .header {{ background-color: {bg_color}; color: white; padding: 20px; border-radius: 5px; }}
          .content {{ margin: 20px 0; padding: 20px; background-color: #f9f9f9; }}
          .alert-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 10px 0; }}
          .critical-box {{ background-color: #f8d7da; border-left: 4px solid #dc3545; padding: 15px; margin: 10px 0; }}
          .info-box {{ background-color: #d1ecf1; border-left: 4px solid #0c5460; padding: 15px; margin: 10px 0; }}
          pre {{ background-color: #f4f4f4; padding: 10px; border-radius: 3px; overflow-x: auto; }}
          .footer {{ margin-top: 30px; padding: 20px; background-color: #e9ecef; border-radius: 5px; }}
          table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
          th {{ background-color: #f2f2f2; }}
          .cmd {{ background-color: #282c34; color: #abb2bf; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
        </style>
      </head>
      <body>
        <div class="header">
          <h2>🚨 MySQL同步系统告警</h2>
          <p style="margin: 5px 0;">生产服务器 → 中间服务器 → Cloud SQL</p>
        </div>
        
        <div class="content">
          <table>
            <tr><th>告警级别</th><td><strong style="color: {bg_color};">{severity}</strong></td></tr>
            <tr><th>告警时间</th><td>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
            <tr><th>中间服务器</th><td>38.246.255.177</td></tr>
            <tr><th>项目路径</th><td>/opt/mysql-sync</td></tr>
          </table>
        </div>
        
        <div class="{'critical-box' if severity == 'CRITICAL' else 'alert-box' if severity in ['HIGH', 'WARNING'] else 'info-box'}">
          <h3>📋 告警内容</h3>
          <pre>{message}</pre>
        </div>
        
        <div class="footer">
          <h3>🔧 快速处理</h3>
          <table>
            <tr>
              <th>操作</th>
              <th>命令</th>
            </tr>
            <tr>
              <td>SSH登录</td>
              <td><span class="cmd">ssh root@38.246.255.177</span></td>
            </tr>
            <tr>
              <td>查看暂停原因</td>
              <td><span class="cmd">cat /opt/mysql-sync/PAUSE_SYNC</span></td>
            </tr>
            <tr>
              <td>查看系统状态</td>
              <td><span class="cmd">bash /opt/mysql-sync/scripts/manage.sh status</span></td>
            </tr>
            <tr>
              <td>查看日志</td>
              <td><span class="cmd">tail -50 /opt/mysql-sync/logs/protection.log</span></td>
            </tr>
            <tr>
              <td>恢复同步</td>
              <td><span class="cmd">bash /opt/mysql-sync/scripts/manage.sh resume</span></td>
            </tr>
          </table>
        </div>
        
        <div style="margin-top: 20px; padding: 10px; text-align: center; color: #666; font-size: 12px;">
          <p>此邮件由 MySQL同步监控系统 自动发送</p>
          <p>发送时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
      </body>
    </html>
    """
    
    text_body = f"""
MySQL同步系统告警

级别: {severity}
时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
服务器: 38.246.255.177

告警内容:
{message}

快速处理:
1. SSH登录: ssh root@38.246.255.177
2. 查看原因: cat /opt/mysql-sync/PAUSE_SYNC
3. 查看状态: bash /opt/mysql-sync/scripts/manage.sh status
4. 恢复同步: bash /opt/mysql-sync/scripts/manage.sh resume
"""
    
    part1 = MIMEText(text_body, 'plain', 'utf-8')
    part2 = MIMEText(html_body, 'html', 'utf-8')
    msg.attach(part1)
    msg.attach(part2)
    
    try:
        print(f"正在连接 {SMTP_SERVER}:{SMTP_PORT}...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10)
        server.starttls()
        
        print(f"正在登录 {SENDER_EMAIL}...")
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        
        print(f"正在发送邮件到 {RECEIVER_EMAIL}...")
        server.send_message(msg)
        server.quit()
        
        print(f"✅ 邮件告警已发送到 {RECEIVER_EMAIL}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ 邮箱认证失败: {e}")
        print("\n💡 提示：")
        print("  1. QQ邮箱需要使用授权码，不是QQ密码")
        print("  2. 获取授权码: 登录QQ邮箱 → 设置 → 账户 → POP3/SMTP服务")
        print("  3. 授权码是16位字符（如: abcdefghijklmnop）")
        return False
    except smtplib.SMTPException as e:
        print(f"❌ SMTP错误: {e}")
        return False
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) > 1:
        subject = "系统告警"
        message = sys.argv[1]
        severity = sys.argv[2] if len(sys.argv) > 2 else 'INFO'
        send_email(subject, message, severity)
    else:
        # 测试邮件
        test_message = f"""
✅ 邮件告警系统配置成功！

这是一封测试邮件，如果您收到此邮件，说明邮件配置正确。

系统信息：
- 中间服务器IP: 38.246.255.177
- 项目路径: /opt/mysql-sync
- 配置时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

下次收到邮件时，表示检测到了以下情况：
• 数据大规模删除
• 表结构异常变更
• 主从复制异常
• 同步连接失败
"""
        send_email("测试邮件", test_message, "INFO")
