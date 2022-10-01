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
from string import Template


#  创建头部
def buildHeader():
    return {
        'Content-Type': 'application/json',
        'X-Forwarded-For': '.'.join(str(random.randint(0, 255)) for x in range(4)),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
        'Origin': 'https://stuhealth.jnu.edu.cn',
        'Referer': 'https://stuhealth.jnu.edu.cn/',
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
        self.proxy = None
        if self.account == "" or self.password == "" or self.email == "" or not utils.EmailHandle("", "").validatePass(
                self.email):
            utils.printErrAndDoLog("Consumer", f"{user_info_dict} init err")
            self.init_flag = False

    def init(self) -> bool:
        return self.init_flag

    def doThreadModel(self, flag: bool, proxy: str, token: str):
        if not self.init():
            return
        if proxy != "":
            self.proxy = {
                "http": proxy,
                "https": proxy
            }
            utils.printInfoAndDoLog("doThreadModel", f"{self.account} 开启线程 With Proxy {self.proxy}")
        else:
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
        utils.printInfoAndDoLog("handlePackage", f"获取到GLOBAL_TOKEN为 {token}")
        jar.set("JNU_AUTH_VERIFY_TOKEN", token)
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
            if self.proxy is None:
                jnuId = self.session.post(
                    'https://stuhealth.jnu.edu.cn/api/user/login',
                    json.dumps({'username': self.account, 'password': password,
                                'validate': validateToken}), headers=header).json()['data']['jnuid']
            else:
                jnuId = self.session.post(
                    'https://stuhealth.jnu.edu.cn/api/user/login',
                    json.dumps({'username': self.account, 'password': password,
                                'validate': validateToken}), headers=header, proxies=self.proxy).json()['data']['jnuid']
            return jnuId
        except Exception as e:
            utils.printErrAndDoLog("getJnuId", e)
            return ''

    # 进行打卡
    def checkin(self):
        info = dict()
        try:
            # 更新接口拿到新的信息
            if self.proxy is None:
                checkinInfo = self.session.post(
                    'https://stuhealth.jnu.edu.cn/api/user/stuinfo',
                    json.dumps({'jnuid': self.jnu_id, "idType": "1"}), headers=buildHeader()).json()
            else:
                checkinInfo = self.session.post(
                    'https://stuhealth.jnu.edu.cn/api/user/stuinfo',
                    json.dumps({'jnuid': self.jnu_id, "idType": "1"}), headers=buildHeader(), proxies=self.proxy).json()
            meta = checkinInfo.get("meta", "")
            code = meta.get("code", -1)
            if meta == "" or code != 2001:  # 2001为定制的
                raise Exception("获取Meta信息错误 拿到历史信息错误")

            # 一次麻烦后面改改部分就OK
            mainTable = Template('{"way2Start":"","language":"cn","declareTime":"$declareTime",'
                                 '"personNo":"$personNo","personName":"$personName","sex":"$sex",'
                                 '"professionName":"$professionName","collegeName":"$collegeName","phoneArea":"+86",'
                                 '"phone":"$phone","assistantName":"$assistantName","assistantNo":"$assistantNo",'
                                 '"className":"$className","linkman":"$linkman","linkmanPhoneArea":"+86",'
                                 '"linkmanPhone":"$linkmanPhone","personHealth":"1","temperature":"35.9",'
                                 '"personHealth2":"0","schoolC1":"$schoolC1","schoolC2":"$schoolC2",'
                                 '"currentArea":"$currentArea", '
                                 '"personC4":"$personC4","personC1id":"$personC1id","personC1":"$personC1",'
                                 '"personC2id":"$personC2id","personC2":"$personC2","personC3id":"$personC3id",'
                                 '"personC3":"$personC3","otherC4":"$otherC4","isPass14C1":"$isPass14C1", '
                                 '"isPass14C2":"$isPass14C2","isPass14C3":"$isPass14C3"}')
            mainTable = mainTable.substitute(
                declareTime=time.strftime('%Y-%m-%d', time.localtime()),
                personNo=checkinInfo['data']['jnuId'],
                personName=checkinInfo['data']['xm'],
                sex=checkinInfo['data']['xbm'],
                professionName=checkinInfo['data']['zy'],
                collegeName=checkinInfo['data']['yxsmc'],
                phone=checkinInfo['data']['mainTable']['phone'],
                assistantName=checkinInfo['data']['mainTable']['assistantName'],
                assistantNo=checkinInfo['data']['mainTable']['assistantNo'],
                className=checkinInfo['data']['mainTable']['className'],
                linkman=checkinInfo['data']['mainTable']['linkman'],
                linkmanPhone=checkinInfo['data']['mainTable']['linkmanPhone'],
                schoolC1=checkinInfo['data']['mainTable']['schoolC1'],
                schoolC2=checkinInfo['data']['mainTable']['schoolC2'],
                currentArea=checkinInfo['data']['mainTable']['currentArea'],
                personC4=checkinInfo['data']['mainTable']['personC4'],
                personC1id=checkinInfo['data']['mainTable']['personC1id'],
                personC1=checkinInfo['data']['mainTable']['personC1'],
                personC2id=checkinInfo['data']['mainTable']['personC2id'],
                personC2=checkinInfo['data']['mainTable']['personC2'],
                personC3id=checkinInfo['data']['mainTable']['personC3id'],
                personC3=checkinInfo['data']['mainTable']['personC3'],
                otherC4=checkinInfo['data']['mainTable']['otherC4'],
                isPass14C1=checkinInfo['data']['mainTable']['isPass14C1'],
                isPass14C2=checkinInfo['data']['mainTable']['isPass14C2'],
                isPass14C3=checkinInfo['data']['mainTable']['isPass14C3'],
            )
            info['mainTable'] = mainTable

            second = checkinInfo['data']['secondTable']
            secondTable = {
                "other20": second['other20'],
                "other24": second['other24'],
                "other28": second['other28'],
                "other30": second['other30'],
                "other32": second['other32'],
                "other34": second['other34'],
                "other1": second['other1'],
                "other3": second['other3'],
                "other5": second['other5'],
                "other4": second['other4'],
                "other7": second['other7'],
                "other6": second['other6'],
                "other9": second['other9'],
                "other8": second['other8'],
                "other10": second['other10'],
                "other11": second['other11'],
                "other12": second['other12'],
                "other14": second['other14'],
                "other15": second['other15'],
                "other16": second['other16'],
                "other17": second['other17'],
                "other18": second['other18'],
                "other19": second['other19'],
                "other21": second['other21'],
                "other22": second['other22'],
                "other23": second['other23'],
                "other25": second['other25'],
                "other26": second['other26'],
                "other27": second['other27'],
                "other29": second['other29'],
                "other31": second['other31'],
                "other33": second['other33']
            }
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
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/92.0.4515.131 Safari/537.36",
                "Accept-Encoding": "gzip, deflate",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            body = dict()
            body['mainTable'] = self.data_bag['mainTable']
            body['secondTable'] = self.data_bag['secondTable']
            body['jnuid'] = self.data_bag['jnuid']
            body_new = json.dumps(body)
            if self.proxy is None:
                results = self.session.post(url, data=body_new, headers=headers).json()
            else:
                results = self.session.post(url, data=body_new, headers=headers, proxies=self.proxy).json()
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


def ConsumerWork(each_info, flag, proxy, token):
    Consumer(each_info).doThreadModel(flag, proxy, token)
