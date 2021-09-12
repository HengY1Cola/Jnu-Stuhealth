import argparse
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPException


parser = argparse.ArgumentParser(
    description='A simple script for sending messages'
)
parser.add_argument(
    '-e',
    '--email',
    required=True,
    type=str,
    help='The Owner Email address is needed！'
)
parser.add_argument(
    '-c',
    '--cookie',
    required=True,
    type=str,
    help='Owner Secret Cookie'
) 
parser.add_argument(
    '-s',
    '--service',
    required=False,
    type=str,
    default="smtp.qq.com",
    help='Choose Your Service'
) 
args = parser.parse_args()

data = time.strftime('%Y-%m-%d', time.localtime(time.time()))

Subject = '打卡成功'
sender = args.email
receivers = [args.email]
receivers = ','.join(receivers) if isinstance(receivers, list) else receivers

message = MIMEMultipart('related')
message['Subject'] = Subject
message['From'] = sender
message['To'] = receivers
content = MIMEText(f'{data} 打卡成功')
message.attach(content)

try:
    server = SMTP_SSL("smtp.qq.com", 465)
    server.login(sender, args.cookie)  # 授权码
    server.sendmail(sender, message['To'].split(','), message.as_string())
    server.quit()
except SMTPException as e:
    raise Exception('发送邮件失败')