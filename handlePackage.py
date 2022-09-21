import json
import random
import requests
import time
from datetime import date, timedelta
from requests.adapters import HTTPAdapter
from urllib3 import Retry
from requests import cookies
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import utils
from handleWechat import WxToken


#  创建头部
def buildHeader():
    return {
        'Content-Type': 'application/json',
        'X-Forwarded-For': '.'.join(str(random.randint(0, 255)) for x in range(4)),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
    }


#  获取随机体温
def randomTemperature() -> str:
    return str(35 + round(random.random(), 1))


# 获取到前一天日期
def getYesDate() -> str:
    return (date.today() + timedelta(days=-1)).strftime("%Y-%m-%d")


class Consumer:
    def __init__(self, user_info_dict: dict):
        self.suitcase = user_info_dict
        self.account = user_info_dict.get("account", "")
        self.password = user_info_dict.get("password", "")
        self.email = user_info_dict.get("email", "")
        self.init_flag = True
        self.session = None
        self.jnu_id = None
        self.data_bag = None
        if self.account == "" or self.password == "" or self.email == "" or not utils.EmailHandle("", "").validatePass(
                self.email):
            utils.printErrAndDoLog("Consumer", f"{user_info_dict} init err")
            self.init_flag = False

    def init(self) -> bool:
        return self.init_flag

    def doThreadModel(self, flag: bool):
        if not self.init():
            return
        utils.printInfoAndDoLog("doThreadModel", f"{self.account} 开启线程")
        unique_token = utils.TOKEN_QUEUE.get()  # 会进入阻塞状态
        self.session = requests.Session()
        self.session.mount(
            'https://',
            HTTPAdapter(
                max_retries=Retry(
                    total=3,
                    backoff_factor=0,
                    status_forcelist=[400, 405, 500, 501, 502, 503, 504]
                )
            )
        )
        jar = requests.cookies.RequestsCookieJar()
        jar.set("JNU_AUTH_VERIFY_COOKIE", WxToken().getToken())
        self.session.cookies.update(jar)
        self.jnu_id = self.getJnuId(unique_token)
        if self.jnu_id == '':
            utils.ERR_PWD.append(self.account)
            utils.printErrAndDoLog("resJnuId", f'{self.account} 拿到JnuId错误')
            return
        utils.printInfoAndDoLog("doThreadModel", f"{self.account} 获取到 {self.jnu_id}")

        self.data_bag = self.checkin()
        if self.data_bag == '':
            utils.FINAL_ERROR.append(self.email)
            utils.printErrAndDoLog("checkin", f"{self.suitcase} 组装不了数据包")
            return
        utils.printInfoAndDoLog("doThreadModel", f"{self.account} 组装好数据包")

        self.postBag(flag)

    def getJnuId(self, validateToken):
        header = buildHeader()
        key = b'xAt9Ye&SouxCJziN'
        cipher = AES.new(key, AES.MODE_CBC, key)
        password = base64.b64encode(cipher.encrypt(pad(self.password.encode(), 16))).decode()
        try:
            jnuId = self.session.post(
                'https://stuhealth.jnu.edu.cn/api/user/login',
                json.dumps({'username': self.account, 'password': password,
                            'validate': validateToken}), headers=header).json()['data']['jnuid']
            return jnuId
        except Exception as e:
            utils.printErrAndDoLog("getJnuId", e)
            return ''

    # 进行打卡
    def checkin(self):
        info = dict()
        try:
            checkinInfo = self.session.post(
                'https://stuhealth.jnu.edu.cn/api/user/stucheckin',
                json.dumps({'jnuid': self.jnu_id}), headers=buildHeader()).json()
            for item in checkinInfo['data']['checkinInfo']:
                if item['flag']:
                    checkinInfo = item
                    break
            lastCheckin = self.session.post(
                'https://stuhealth.jnu.edu.cn/api/user/review',
                json.dumps({'jnuid': self.jnu_id, 'id': str(checkinInfo["id"])}), headers=buildHeader()).json()['data']

            mainTable = {k: v for k, v in lastCheckin['mainTable'].items() if
                         v != '' and not k in ['personType', 'createTime', 'del', 'id', 'other', 'passAreaC2',
                                               'passAreaC3',
                                               'passAreaC4', 'temperature']}
            mainTable['declareTime'] = time.strftime('%Y-%m-%d', time.localtime())  # 当日日期
            mainTable['temperature'] = randomTemperature()  # 当日体温
            mainTable['way2Start'] = ''
            info['mainTable'] = mainTable

            if lastCheckin['secondTable'] is None:
                if 'inChina' not in mainTable:
                    mainTable['inChina'] = '1'
                for key in ['personC1', 'personC1id', 'personC2', 'personC2id', 'personC3', 'personC3id', 'personC4']:
                    if key not in mainTable:
                        mainTable[key] = ''
                if mainTable['inChina'] == '1':
                    secondTable = {
                        'other1': mainTable['inChina'],
                        'other3': mainTable['personC4'],
                        'other4': mainTable['personC1'],
                        'other5': mainTable['personC1id'],
                        'other6': mainTable['personC2'],
                        'other7': mainTable['personC2id'],
                        'other8': mainTable['personC3'],
                        'other9': mainTable['personC3id'],
                    }
                else:
                    secondTable = {
                        'other1': mainTable['inChina'],
                        'other2': mainTable['countryArea'],
                        'other3': mainTable['personC4'],
                    }
            else:
                secondTable = {k: v for k, v in lastCheckin['secondTable'].items() if
                               v != '' and not k in ['mainId', 'id']}
                secondTable['other12'] = ''
            # 补充新的信息 => 早上/中午/晚上检查
            secondTable['other29'] = randomTemperature()  # 早上
            secondTable['other30'] = getYesDate()  # 早上
            secondTable['other31'] = randomTemperature()  # 中午
            secondTable['other32'] = getYesDate()  # 中午
            secondTable['other33'] = randomTemperature()  # 晚上
            secondTable['other34'] = getYesDate()  # 晚上
            info['secondTable'] = secondTable
            info['jnuid'] = self.jnu_id
            return info
        except Exception as e:
            utils.printErrAndDoLog("checkin", e)
            return ''

    def postBag(self, flag):
        try:
            data = time.strftime('%Y-%m-%d', time.localtime(time.time()))
            url = "https://stuhealth.jnu.edu.cn/api/write/main"
            headers = {
                "Host": "stuhealth.jnu.edu.cn",
                "Content-Type": "application/json",
                "Accept": "application/json, text/plain, */*",
                "Origin": "https://stuhealth.jnu.edu.cn",
                "Referer": "https://stuhealth.jnu.edu.cn/",  # 必须带这个参数，不然会报错
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            body = dict()
            self.data_bag['mainTable']['declareTime'] = data
            body['mainTable'] = self.data_bag['mainTable']
            body['secondTable'] = self.data_bag['secondTable']
            body['jnuid'] = self.data_bag['jnuid']
            body_new = json.dumps(body)
            results = self.session.post(url, data=body_new, headers=headers).json()
            if results['meta']['code'] == 6666:
                utils.SUCCESS.append(self.email)
                utils.printInfoAndDoLog("postBag", f"{self.account} 打卡成功")
            elif results['meta']['code'] == 1111:
                utils.REPEAT.append(self.email)
                utils.printInfoAndDoLog("postBag", f"{self.account} 重复打卡")
            else:
                if flag:
                    utils.DEAD_LATER.append(self.suitcase)
                    utils.printInfoAndDoLog("postBag", f"{self.account} 加入死信队列")
                else:
                    utils.FINAL_ERROR.append(self.email)

        except Exception as e:
            utils.printErrAndDoLog("postBag", e)


def ConsumerWork(each_info, flag):
    Consumer(each_info).doThreadModel(flag)
