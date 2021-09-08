import logging
import struct
import os
from PIL import Image
from datetime import datetime, date
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPException
import queue

# --------------------- 需要填写的信息 ---------------------
SEND_EMAIL = ''  # 邮件注册
AUTH_REGISTERED = ""  # 授权码
CURRENT_PATH = os.path.dirname(__file__)
BG_IMG_PATH = os.path.join(CURRENT_PATH, 'bgImg')
LOG_PATH = os.path.join(CURRENT_PATH, 'log')
TOKEN_QUEUE, TOTAL_QUEUE = queue.Queue(0), queue.Queue(0)
SUCCESS, REPEAT, ERROR = [], [], []

# --------------------- 默认配置 ---------------------
banner = '''
     _             ____  _         _   _            _ _   _     
    | |_ __  _   _/ ___|| |_ _   _| | | | ___  __ _| | |_| |__  
 _  | | '_ \| | | \___ \| __| | | | |_| |/ _ \/ _` | | __| '_ \ 
| |_| | | | | |_| |___) | |_| |_| |  _  |  __/ (_| | | |_| | | |
 \___/|_| |_|\__,_|____/ \__|\__,_|_| |_|\___|\__,_|_|\__|_| |_|
'''

fileName = os.path.join(LOG_PATH, date.today().strftime("%Y_%m") + ".log")
timeNow = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
# todo 设置日志
logging.basicConfig(level=logging.INFO,
                    filename=fileName,
                    datefmt='%Y/%m/%d %H:%M:%S',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(lineno)d - %(module)s - %(message)s')
logger = logging.getLogger(__name__)


# ---------------------仓库函数 ---------------------

# 获取文本
def getTxt(Path):
    with open(Path, "r") as f:
        return [str(each).replace('\n', '') for each in f.readlines()]


# 获取图片的dHash
def getImageHash(img: Image) -> bytes:
    img = img.convert('L').resize((17, 16), Image.LANCZOS)
    imgBytes = img.tobytes()
    imgHash = [0 for _ in range(16)]
    for i in range(16):
        for j in range(16):
            if imgBytes[(i << 4) + j] < imgBytes[(i << 4) + j + 1]:
                imgHash[i] |= 1 << j
    return struct.pack('<HHHHHHHHHHHHHHHH', *imgHash)


# 计算两个dHash之间的汉明距离，范围是0-256，越低则图片越相似
def getImageHashDiff(hashA: bytes, hashB: bytes) -> int:
    diff = 0
    for a, b in zip(hashA, hashB):
        diff += (
            0, 1, 1, 2, 1, 2, 2, 3, 1, 2, 2, 3, 2, 3, 3, 4,
            1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
            1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
            2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
            1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
            2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
            2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
            3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
            1, 2, 2, 3, 2, 3, 3, 4, 2, 3, 3, 4, 3, 4, 4, 5,
            2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
            2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
            3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
            2, 3, 3, 4, 3, 4, 4, 5, 3, 4, 4, 5, 4, 5, 5, 6,
            3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
            3, 4, 4, 5, 4, 5, 5, 6, 4, 5, 5, 6, 5, 6, 6, 7,
            4, 5, 5, 6, 5, 6, 6, 7, 5, 6, 6, 7, 6, 7, 7, 8,
        )[a ^ b]
    return diff


# 计算多项式，每一项是pn * (x ** n)
def polynomialCalc(x: float, params) -> float:
    return sum(p * (x ** n) for n, p in enumerate(params))


def untilFindElement(by: By, value: str):
    def func(oneBrowser) -> bool:
        try:
            oneBrowser.find_element(by, value)
            return True
        except NoSuchElementException:
            return False

    return func


#  打印并写入日志
def printAndLog(strInfo):
    print(strInfo)
    logging.info(strInfo)


# 发送邮件
def send(subject, text, email, send_email, auth):
    """
    :param auth: 授权码
    :param send_email: 发件人邮件（于授权码匹配）
    :param subject: 邮件标题
    :param text: 邮件文本
    :param email: 邮箱
    :return:
    """
    Subject = subject
    sender = send_email  # 发件人邮箱
    receivers = email  # 收件人邮箱
    receivers = ','.join(receivers) if isinstance(receivers, list) else receivers

    message = MIMEMultipart('related')
    message['Subject'] = Subject
    message['From'] = sender
    message['To'] = receivers  # 处理多人邮箱
    content = MIMEText(text)
    message.attach(content)

    try:
        server = SMTP_SSL("smtp.qq.com", 465)
        server.login(sender, auth)  # 授权码
        server.sendmail(sender, message['To'].split(','), message.as_string())
        server.quit()
    except SMTPException as e:
        printAndLog("发送邮件失败", e)
        pass
