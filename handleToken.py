import io
import threading
import time
import urllib.parse

import qrcode
from pyzbar.pyzbar import decode
import requests
from utils import *

JNU_TOKEN_QUEUE = queue.Queue(0)


class Token:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                                                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                                                   'Chrome/105.0.0.0 Safari/537.36'})
        self.Token = ""

    @staticmethod
    def getCodeUrl(pageSource):
        regex = r"<img class=\"web_qrcode_img\" src=\"(.*)\"/>"
        matches = re.findall(regex, pageSource, re.MULTILINE)
        if len(matches) == 1:
            if matches[0] != '':
                return f"https://open.weixin.qq.com{matches[0]}"
            return ""
        else:
            return ""

    def emailNotice(self, url, email_handle):
        setting = readSettings()
        aimEmail = setting.get("notice", "")
        if not EmailHandle("", "").validatePass(aimEmail) or aimEmail == "":
            aimEmail = ParseHandle().readJsonInfo().get("auth_email")
        email_handle.doNotice("请尽快进行微信验证", [aimEmail], f'<img src="{url}"/>')
        printInfoAndDoLog("emailNotice", f'微信验证通知发送成功并开始进行轮询验证')
        aimCode = str(url).split("/")[-1]
        start = int(time.time())
        while self.Token == '' and int(time.time()) - start <= 60 * 20:
            self.Token = self.judgeState(aimCode)
        time.sleep(1)
        printInfoAndDoLog("emailNotice", f'轮询完成 token {self.Token} start {start} end {int(time.time())}')
        JNU_TOKEN_QUEUE.put(self.Token)

    def qrNotice(self, url):
        printInfoAndDoLog("qrNotice", f"图片地址：{url}")
        barcode_url = ''
        barcodes = decode(Image.open(io.BytesIO(requests.session().get(url).content)))
        for barcode in barcodes:
            barcode_url = barcode.data.decode("utf-8")

        qr = qrcode.QRCode()
        qr.add_data(barcode_url)
        qr.print_ascii(invert=True)
        time.sleep(1)
        printInfoAndDoLog("qrNotice", "请扫码进行验证，并开始轮询状态")
        aimCode = str(url).split("/")[-1]
        start = int(time.time())
        while self.Token == '' and int(time.time()) - start <= 60 * 20:
            self.Token = self.judgeState(aimCode)
        time.sleep(1)
        printInfoAndDoLog("emailNotice", f'轮询完成 token {self.Token} start {start} end {int(time.time())}')
        JNU_TOKEN_QUEUE.put(self.Token)

    @staticmethod
    def judgeState(code):
        try:
            r = requests.get(f'https://lp.open.weixin.qq.com/connect/l/qrconnect'
                             f'?uuid={code}&_={int(time.time())}',
                             headers={'User-Agent': "Mozilla/5.0 (Macintosh; "
                                                    "Intel Mac OS X 10.15; rv:105.0) Gecko/20100101 Firefox/105.0"},
                             timeout=10)
            if r.status_code == 200:  # window.wx_errcode=404;window.wx_code='';
                regex = r"window.wx_errcode=.*?;window.wx_code='(.*)'"
                matches = re.findall(regex, str(r.text), re.MULTILINE)
                if len(matches) == 1:
                    return matches[0]
                return ""
            else:
                return ""
        except requests.exceptions.Timeout as e:
            printErrAndDoLog("judgeState", f"本次轮询超时 {e}")
            return ""

    @staticmethod
    def __parseLocation(html):
        try:
            regex = r".*?window.location.replace\(\'(.*)\'\);.*?"
            matches = re.findall(regex, html, re.MULTILINE | re.IGNORECASE)
            if len(matches) != 2:
                raise Exception("matches 没有找到微信认证链接")
        except Exception as e:
            printErrAndDoLog("parseLocation", e)
            raise e
        else:
            return matches[1]  # 返回PC

    @staticmethod
    def __parseWechatUrl(url):
        try:
            query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query))
            aim_url = query.get('redirect_uri', "")
            if aim_url == "":
                raise Exception("微信重定向激活失败")
        except Exception as e:
            printErrAndDoLog("doGet", e)
            raise e
        else:
            decode_url = urllib.parse.unquote(aim_url)
            decode_dict = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(decode_url).query))
            return decode_dict['verifyID']

    def __getToken(self, code, verify_id):
        url = f'https://auth7.jnu.edu.cn//wechat_auth/wechat/wechatScanAsync?verifyID={verify_id}&code={code}&state='
        r = self.session.get(url)
        if r.status_code != 200:
            raise Exception("获取拼凑好了的链接错误")
        if len(r.history) != 2:
            raise Exception("获取getLocation len 错误")
        cookie = r.history[1].cookies
        cookie_dict = requests.utils.dict_from_cookiejar(cookie)
        return cookie_dict.get("JNU_AUTH_VERIFY_TOKEN", "")

    def doMission(self, email_handle):
        printInfoAndDoLog("doMission", "准备开始到微信认证页面")
        r = self.session.get("https://stuhealth.jnu.edu.cn/#/login", timeout=15)
        if r.status_code != 200:
            raise Exception("获取跳转微信页面错误")
        wechat = self.__parseLocation(r.text)
        verify_id = self.__parseWechatUrl(wechat)
        printInfoAndDoLog("doMission", f"get verify_id {verify_id}")
        r = self.session.get(wechat, timeout=15)
        if r.status_code != 200:
            raise Exception("获取微信页面错误")
        aimUrl = self.getCodeUrl(r.text)
        printInfoAndDoLog("doMission", "微信图片链接")
        if aimUrl == "":
            printErrAndDoLog("doMission", "微信图片链接获取错误")
            raise Exception("微信图片链接获取错误")
        # printInfoAndDoLog("doMission", "准备开启线程进行邮件通知以及轮询")
        # noticeThread = threading.Thread(target=self.emailNotice(aimUrl, email_handle))
        # noticeThread.start()
        printInfoAndDoLog("doMission", "准备打印微信验证码")
        noticeThread = threading.Thread(target=self.qrNotice(aimUrl))
        noticeThread.start()
        try:
            code = JNU_TOKEN_QUEUE.get(timeout=60 * 20)  # 花费40分钟等待信号回来
        except Exception as e:
            printErrAndDoLog("doMission", f"等待信号回归 {e}")
            raise e
        else:  # 这个时候已经进行了认证 不进行重试了
            time.sleep(1)
            token = self.__getToken(code, verify_id)
            if token == "":
                raise Exception("token获取失败")
            return token

    def runMain(self, email_handle, times):
        if times >= 3:
            printErrAndDoLog("runMain", f"超过最大重试次数")
            return ""
        try:
            token = self.doMission(email_handle)
            return token
        except Exception as e:
            printErrAndDoLog("runMain", f"Exception is {e}")
            if str(e) == "获取微信页面错误" or str(e) == "微信图片链接获取错误" or str(e) == "获取跳转微信页面错误":
                printErrAndDoLog("runMain", f"微信页面加载不出来 or 微信图片链接获取错误")
                return self.runMain(email_handle, times + 1)
            return ""


if __name__ == "__main__":
    Token().runMain("", 1)
