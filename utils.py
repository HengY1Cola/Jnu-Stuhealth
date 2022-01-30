import struct
import os
import sys
import datetime
from PIL import Image
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.by import By
import queue

SEND_EMAIL = ''
AUTH_REGISTERED = ""
CURRENT_PATH = os.path.dirname(__file__)
BG_IMG_PATH = os.path.join(CURRENT_PATH, 'bgImg')
TOKEN_QUEUE, TOTAL_QUEUE = queue.Queue(0), queue.Queue(0)
SUCCESS, REPEAT, ERROR = [], [], []
banner = '''
     _             ____  _         _   _            _ _   _     
    | |_ __  _   _/ ___|| |_ _   _| | | | ___  __ _| | |_| |__  
 _  | | '_ \| | | \___ \| __| | | | |_| |/ _ \/ _` | | __| '_ \ 
| |_| | | | | |_| |___) | |_| |_| |  _  |  __/ (_| | | |_| | | |
 \___/|_| |_|\__,_|____/ \__|\__,_|_| |_|\___|\__,_|_|\__|_| |_|
'''


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


# 写入到日志
def makePrint2File(path='./'):
    class Logger(object):
        def __init__(self, filename="Default.log", path="./"):
            self.terminal = sys.stdout
            self.log = open(os.path.join(path, filename), "a", encoding='utf8', )

        def write(self, message):
            self.terminal.write(message)
            self.log.write(message)

        def flush(self):
            pass

    fileName = datetime.datetime.now().strftime('day' + '%Y_%m_%d')
    sys.stdout = Logger(fileName + '.log', path=path)
    print(fileName.center(60, '*'))
