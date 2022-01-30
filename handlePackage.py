import json
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from smtplib import SMTP_SSL, SMTPException
import requests
import time
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from utils import TOKEN_QUEUE, SUCCESS, ERROR, REPEAT, TOTAL_QUEUE


# 获得JnuId
def getJnuId(eachInfo, validateToken):
    header = {
        'Content-Type': 'application/json',
        'X-Forwarded-For': '.'.join(str(random.randint(0, 255)) for x in range(4)),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
    }

    s = requests.Session()
    s.mount(
        'https://',
        HTTPAdapter(
            max_retries=Retry(
                total=3,
                backoff_factor=0,
                status_forcelist=[400, 405, 500, 501, 502, 503, 504]
            )
        )
    )
    key = b'xAt9Ye&SouxCJziN'
    cipher = AES.new(key, AES.MODE_CBC, key)
    password = base64.b64encode(cipher.encrypt(pad(eachInfo['password'].encode(), 16))).decode()
    password = password.replace('+', '-', 1).replace('/', '_', 1).replace('=', '*', 1)
    try:
        jnuId = s.post(
            'https://stuhealth.jnu.edu.cn/api/user/login',
            json.dumps({
                'username': eachInfo['account'],
                'password': password,
                'validate': validateToken
            }),
            headers=header
        ).json()['data']['jnuid']
        return jnuId
    except Exception as e:
        print(e)
        return ''


#  创建头部
def buildHeader():
    return {
        'Content-Type': 'application/json',
        'X-Forwarded-For': '.'.join(str(random.randint(0, 255)) for x in range(4)),
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; Trident/7.0; Touch; rv:11.0) like Gecko',
    }


# 进行打卡
def checkin(jnuid):
    s = requests.Session()  # 创建Session会话
    s.mount(
        'https://',
        HTTPAdapter(
            max_retries=Retry(
                total=3,  # 设置重试次数
                backoff_factor=0,
                status_forcelist=[400, 405, 500, 501, 502, 503, 504]
            )
        )
    )
    info = dict()

    try:
        # 获取每日打卡记录
        checkinInfo = s.post(
            'https://stuhealth.jnu.edu.cn/api/user/stucheckin',
            json.dumps({
                'jnuid': jnuid,
            }),
            headers=buildHeader()
        ).json()
        if not checkinInfo['meta']['success']:
            raise Exception('Invalid JNUID')
        for item in checkinInfo['data']['checkinInfo']:
            if item['flag']:
                checkinInfo = item
                break
        # 获取昨日打卡的数据
        lastCheckin = s.post(
            'https://stuhealth.jnu.edu.cn/api/user/review',
            json.dumps({
                'jnuid': jnuid,
                'id': str(checkinInfo["id"]),
            }),
            headers=buildHeader()
        ).json()['data']
        # 组装mainTable
        mainTable = {k: v for k, v in lastCheckin['mainTable'].items() if
                     v != '' and not k in ['personType', 'createTime', 'del', 'id', 'other', 'passAreaC2', 'passAreaC3',
                                           'passAreaC4']}
        mainTable['declareTime'] = time.strftime('%Y-%m-%d', time.localtime())
        mainTable['way2Start'] = ''
        info['mainTable'] = mainTable
        # 组装secondTable
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
            elif mainTable['inChina'] == '2':
                secondTable = {
                    'other1': mainTable['inChina'],
                    'other2': mainTable['countryArea'],
                    'other3': mainTable['personC4'],
                }
        else:
            secondTable = {k: v for k, v in lastCheckin['secondTable'].items() if v != '' and not k in ['mainId', 'id']}
            secondTable['other12'] = ''
        info['secondTable'] = secondTable
        info['jnuid'] = jnuid
        return info
    except Exception as ex:
        raise Exception('获取打卡信息失败')


# 开始发包
def post_bag(one):
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
    one['mainTable']['declareTime'] = data
    body['mainTable'] = one['mainTable']
    body['secondTable'] = one['secondTable']
    body['jnuid'] = one['jnuid']
    body_new = json.dumps(body)
    results = requests.post(url, data=body_new, headers=headers).text
    false = False
    true = True
    results = eval(results)
    if results['meta']['code'] == 6666:
        return {
            'state': 'success',
            'msg': f"{one['mainTable']['personName']} 打卡成功",
            'code': 0,
        }
    elif results['meta']['code'] == 1111:
        return {
            'state': 'repeat',
            'msg': f"{one['mainTable']['personName']} 重复打卡",
            'code': 1,
        }
    else:
        return {
            'state': 'error',
            'msg': f"{one['mainTable']['personName']} 打卡失败",
            'code': 2,
        }


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
        print("发送邮件失败", e)
        pass


# 多线程模式
def threadModel(eachInfo):
    print(f'- {eachInfo["account"]} 开启了线程')
    oneToken = TOKEN_QUEUE.get()
    resJnuId = getJnuId(eachInfo, oneToken)
    TOTAL_QUEUE.put("done")
    if resJnuId != '':
        bag = checkin(resJnuId)
        res = post_bag(bag)
        if res['code'] == 0:
            SUCCESS.append(eachInfo['email'])
            print('- {} 打卡成功'.format(eachInfo["account"]))
        elif res['code'] == 1:
            REPEAT.append(eachInfo['email'])
            print('- {} 重复打卡'.format(eachInfo["account"]))
        else:
            ERROR.append(eachInfo['email'])
            print('- {} 打卡错误'.format(eachInfo["account"]))
    else:
        ERROR.append(eachInfo['email'])
        print('- {} 打卡错误'.format(eachInfo["account"]))
    print(f'- {eachInfo["account"]} 结束了线程')
    return True
