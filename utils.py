import json
import logging
import re
import struct
import os
from PIL import Image
from datetime import datetime, date
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPException, SMTPAuthenticationError
import queue
from handlePackage import Consumer

# --------------------- 初始化路径信息 ---------------------
CURRENT_PATH = os.path.dirname(__file__)
BG_IMG_PATH = os.path.join(CURRENT_PATH, 'bgImg')
LOG_PATH = os.path.join(CURRENT_PATH, 'log')
HIDE_HEADER = os.path.join(CURRENT_PATH, 'hideHeader')
BIN_DRIVER = os.path.join(CURRENT_PATH, 'bin')
JSON_PATH = os.path.join(CURRENT_PATH, 'user_info.json')
SETTING_PATH = os.path.join(CURRENT_PATH, 'setting.json')

# --------------------- 初始化变量 ---------------------
TOKEN_QUEUE = queue.Queue(0)
PROXY_QUEUE = queue.Queue(0)
ERR_PWD, SUCCESS, REPEAT, DEAD_LATER, FINAL_ERROR, = [], [], [], [], []


# ---------------------仓库函数 ---------------------

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


class ParseHandle:
    def __init__(self):
        self.json_path = JSON_PATH  # 写死到这里读取文件

    def readJsonInfo(self) -> dict:
        try:
            with open(self.json_path, 'r', encoding="utf-8") as f:
                load_dict = json.load(f)
                printInfoAndDoLog("readJsonInfo", str(load_dict))
                return load_dict
        except Exception as e:
            printErrAndDoLog("readJsonInfo", e)
            raise e

    def doParse(self):
        parse_json = self.readJsonInfo()
        auth_email = parse_json.get("auth_email", "")
        auth_code = parse_json.get("auth_code", "")
        auth_service = parse_json.get("auth_service", "smtp.qq.com")
        user_list = parse_json.get("user_list", [])
        if len(user_list) == 0:
            printInfoAndDoLog("doParse", "user_list len is 0")
            raise Exception("user_list len is 0")
        email_validator = EmailHandle(auth_email, auth_code, auth_service)
        if auth_code == "" or auth_email == "" or not email_validator.validatePass(
                auth_email) or not email_validator.validateAuth():
            printInfoAndDoLog("doParse", "email error")
            raise Exception("email error")
        user_list_final = []
        for each in user_list:
            if Consumer(each).init():
                user_list_final.append(each)
        printInfoAndDoLog("doParse", "处理共 {} 打卡信息".format(len(user_list_final)))
        return email_validator, user_list_final


class EmailHandle:
    def __init__(self, email_str, auth_code, service="smtp.qq.com"):
        self.authEmail = email_str
        self.authCode = auth_code
        self.authService = service

    @staticmethod
    def validatePass(email_str) -> bool:
        return False if not re.match(r'^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$', email_str) else True

    def validateAuth(self) -> bool:
        try:
            server = SMTP_SSL(self.authService, 465)
            server.login(self.authEmail, self.authCode)
            server.quit()
            return True
        except SMTPAuthenticationError:
            return False

    def doNotice(self, title, toEmailList, msg):
        message = MIMEMultipart('related')
        message['Subject'] = title
        message['From'] = self.authEmail
        message['To'] = ','.join(toEmailList) if isinstance(toEmailList, list) else toEmailList
        message.attach(MIMEText(msg))
        try:
            server = SMTP_SSL(self.authService, 465)
            server.login(self.authEmail, self.authCode)  # 授权码
            server.sendmail(self.authEmail, message['To'].split(','), message.as_string())
            server.quit()
            return None
        except Exception as e:
            return e


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
logging.basicConfig(level=logging.INFO,
                    filename=fileName,
                    datefmt='%Y/%m/%d %H:%M:%S',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def printInfoAndDoLog(funcName, info):
    info_str = f"[*] {funcName} {info}"
    print(info_str)
    logging.info(funcName + info)


def printErrAndDoLog(funcName, error):
    err_str = f"[X] {funcName} account error: {error}"
    print(err_str)
    logging.warning(err_str)


def readSettings() -> dict:
    try:
        with open(SETTING_PATH, 'r', encoding="utf-8") as f:
            load_dict = json.load(f)
            return load_dict
    except Exception as e:
        printErrAndDoLog("readJsonInfo", e)
        raise e
