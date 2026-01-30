#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
邮件告警通知 - QQ邮箱版
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import sys

# QQ邮箱SMTP配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 587  # 或使用SSL的465端口
SENDER_EMAIL = "1657703776@qq.com"           # 你的QQ邮箱
SENDER_PASSWORD = "kdamvydlotdlcgdb"  # QQ邮箱授权码
RECEIVER_EMAIL = "1657703776@qq.com"    # 接收邮箱

# 使用与Gmail相同的发送函数...
# （代码与上面Gmail版本相同，只是SMTP服务器不同）
