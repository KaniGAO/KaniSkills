"""SMTP 邮件发送模块"""
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import Config


def send_report(
    report_path: str,
    subject: str = None,
    recipients: list[str] = None,
) -> bool:
    """通过 Gmail SMTP 发送日报附件"""
    sender = Config.GMAIL_SENDER_EMAIL
    password = Config.GMAIL_APP_PASSWORD
    recipients = recipients or Config.RECIPIENT_EMAILS or []

    if not sender or not password:
        print("  [Email] GMAIL_SENDER_EMAIL or GMAIL_APP_PASSWORD not configured")
        return False

    if not recipients:
        print("  [Email] No recipients configured")
        return False

    now = datetime.now(timezone.utc) + timedelta(hours=8)
    subject = subject or f"Global Markets Daily Briefing — {now.strftime('%B %d, %Y')}"

    # 构建邮件
    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject

    body = f"""Hi Team,

Attached is today's Global Markets Daily Briefing.

Prepared: {now.strftime('%A, %B %d, %Y at %I:%M %p HKT')}

This briefing covers:
• Monthly Macro Calendar
• Today's Events
• Overnight Market Recap
• Latest Macro Developments
• Central Bank Monitor
• Interview Talking Points
• Day Ahead — Asia Session Focus
• Key Levels Dashboard

--
Prepared for educational and interview preparation purposes only.
Does not constitute investment advice.
"""
    msg.attach(MIMEText(body, "plain"))

    # 附件
    report_name = os.path.basename(report_path)
    with open(report_path, "rb") as f:
        attachment = MIMEBase("application", "octet-stream")
        attachment.set_payload(f.read())
    encoders.encode_base64(attachment)
    attachment.add_header(
        "Content-Disposition",
        f"attachment; filename={report_name}",
    )
    msg.attach(attachment)

    # 发送
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(sender, password)
            server.send_message(msg)
        print(f"  [Email] Report sent to {len(recipients)} recipient(s)")
        print(f"  [Email] Recipients: {recipients}")
        return True
    except smtplib.SMTPAuthenticationError:
        print("  [Email] Gmail authentication failed. Check GMAIL_APP_PASSWORD.")
        print("  [Email] Note: Use App Password (not regular password).")
        return False
    except smtplib.SMTPException as e:
        print(f"  [Email] SMTP error: {e}")
        return False
