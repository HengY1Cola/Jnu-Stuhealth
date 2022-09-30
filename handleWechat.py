import requests
import urllib.parse
from utils import *
import re


class WxToken:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36'})

    def __doGet(self):
        try:
            req = self.session.get("https://stuhealth.jnu.edu.cn")
            if req.status_code == 200:
                if len(req.history) != 1:  # 现在修改为1次
                    raise Exception("打卡网站重定向逻辑错误")
                first_re = req.history[0].headers
                query = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(first_re['Location']).query))
                verify_id = query.get("verifyID", "")
                if verify_id == "":
                    raise Exception("verify_id获取失败")
            else:
                raise Exception("打卡网站错误")
        except Exception as e:
            printErrAndDoLog("doGet", e)
            raise e
        else:
            return req.text, verify_id

    @staticmethod
    def __parseLocation(html):
        try:
            regex = r".*?window.location.replace\(\'(.*)\'\);.*?"
            matches = re.findall(regex, html, re.MULTILINE | re.IGNORECASE)
            if len(matches) != 2:
                raise Exception("matches 没有找到微信认证链接")
        except Exception as e:
            printErrAndDoLog("doGet", e)
            raise e
        else:
            return matches[0]  # 返回为手机认证的

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
            return aim_url

    def __getToken(self, aim_url):
        try:
            req = self.session.get(aim_url)
            if req.status_code == 200:
                if len(req.history) != 2:
                    raise Exception("认证网站重定向逻辑错误")
                set_cookie = req.history[1].headers
                token = set_cookie.get("Set-Cookie", "")
                if token == "":
                    raise Exception("token获取失败")
                regex = r".*?JNU_AUTH_VERIFY_TOKEN=(.*?);.*?"
                matches = re.findall(regex, token, re.MULTILINE | re.IGNORECASE)
                if len(matches) != 1:
                    raise Exception("token 格式错误")
            else:
                raise Exception("打卡网站错误")
        except Exception as e:
            printErrAndDoLog("doGet", e)
            raise e
        else:
            return matches[0]

    def getActiveUrl(self):
        active = None
        for _ in range(3):
            try:
                locationReplace, verify_id = self.__doGet()
                wechat_url = self.__parseLocation(locationReplace)
                active = self.__parseWechatUrl(wechat_url)
                break
            except Exception as e:
                printErrAndDoLog("getActiveUrl", e)
                continue
        if active is None:
            raise Exception("getActiveUrl 获取失败")
        else:
            return active

    def getToken(self):
        verify_token = None
        for _ in range(3):
            try:
                locationReplace, verify_id = self.__doGet()
                wechat_url = self.__parseLocation(locationReplace)
                activeUrl = self.__parseWechatUrl(wechat_url)
                verify_token = self.__getToken(activeUrl)
                break
            except Exception as e:
                printErrAndDoLog("getToken", e)
                continue
        if verify_token is None:
            raise Exception("getToken 获取失败")
        else:
            return verify_token
