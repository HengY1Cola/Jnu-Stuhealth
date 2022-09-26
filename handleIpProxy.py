import requests

from utils import readSettings, printInfoAndDoLog, printErrAndDoLog


class IpProxy:
    def __init__(self):
        setting = readSettings()
        proxy = setting['proxy']
        printInfoAndDoLog("IpProxy", "高匿代理仅在 服务器下有效")
        self.neek = proxy.get("neek", "")  # 在setting里面配置
        self.appkey = proxy.get("appkey", "")
        self.ip = proxy.get("ip", "")  # 这个只认服务器 走网关出来的没法判断
        self.ret_data = ""
        if self.neek == '' or self.appkey == '' or self.ip == '':
            raise Exception("无代理配置")

    def addWhite(self):
        url = f'https://wapi.http.linkudp.com/index/index/save_white?neek={self.neek}&appkey={self.appkey}&white={self.ip}'
        r = requests.get(url)
        info = r.json()
        if info['code'] == 0:
            printInfoAndDoLog('addWhite', f'添加 {self.ip} 成功')
        elif info['code'] == 115:
            printInfoAndDoLog('addWhite', f'{self.ip} 重复添加但是验证成功')
        else:
            printErrAndDoLog('addWhite', f'高匿代理失败 {info["msg"]}')
            raise Exception("代理使用失败 检查配置")

    def GetNumProxy(self, num):
        self.addWhite()
        proxy = readSettings()['proxy']
        pack = proxy.get("pack", "")
        if pack == "":
            printErrAndDoLog('GetNumProxy', f'代理用户套餐ID为空 请到代理网站查询')
            printInfoAndDoLog('GetNumProxy', "个人中心->套餐中心->终身免费VIP套餐->点击获取余量->找到ac这个参数就是")
            raise Exception("代理用户套餐ID为空 请到代理网站查询")
        if num >= 20:
            printErrAndDoLog('GetNumProxy', f'芝麻代理免费数量为20个 自行购买可注释此处 https://www.zmhttp.com/')
            raise Exception("芝麻代理免费数量为20个")
        aimUrl = f'http://webapi.http.zhimacangku.com/getip?num={num}&type=2&pro=440000&city=440100' \
                 f'&yys=0&port=1&pack={pack}&ts=0&ys=0&cs=0&lb=1&sb=0&pb=4&mr=1&regions='
        r = requests.get(aimUrl)
        info = r.json()
        if info['code'] != 0:
            printErrAndDoLog('GetNumProxy', f'芝麻代理获取失败, 开始准备进行登陆激活今日免费包')
            try:
                self.activeBag()
            except Exception as e:
                printErrAndDoLog('GetNumProxy', f'发生错误 {e}')
                raise Exception("芝麻代理获取失败请尽快检查")
        ipUrlList = []
        for each in info['data']:
            ipUrlList.append(f'http://{each["ip"]}:{each["port"]}')
        return ipUrlList

    def activeBag(self):
        proxy = readSettings()['proxy']
        account = proxy.get("account", "")
        password = proxy.get("password", "")
        if account == "" or password == "":
            printErrAndDoLog('activeBag', f'账号/密码为空 不进行登陆')
            raise Exception("账号/密码为空 不进行登陆")
        s = requests.session()
        data = {
            "phone": account,
            "password": password,
            "remember": "0"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.zmhttp.com",
            "Referer": "https://www.zmhttp.com/"
        }
        # 进行登陆
        r = s.post("https://uwapi.http.linkudp.com/index/users/login_do", headers=headers, data=data)
        if r.status_code == 200:
            info = r.json()
            self.ret_data = info.get("ret_data", "")
            if self.ret_data == "":
                printErrAndDoLog('activeBag', f'账号/密码错误, 无法获取ret_data')
                raise Exception("账号/密码错误, 无法获取ret_data")
        else:
            printErrAndDoLog('activeBag', f'账号/密码获取错误 code {r.status_code}')
            raise Exception(f'账号/密码获取错误 code {r.status_code}')
        # 激活对应的链接
        data = {
            "geetest_challenge": "",
            "geetest_validate": "",
            "geetest_seccode": ""
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://www.zmhttp.com",
            "Referer": "https://www.zmhttp.com/",
            "Session-Id": self.ret_data,
        }
        r = s.post("https://uwapi.http.linkudp.com/index/users/get_day_free_pack", headers=headers, data=data)
        if r.status_code == 200:
            info = r.json()
            msg = info.get("msg", "")
            if msg == "ok" or msg == "今日已经领取过免费ip":
                printInfoAndDoLog('activeBag', f'获取免费 {msg}')
                return
            else:
                printErrAndDoLog('activeBag', f'获取免费激活错误 info {info}')
                raise Exception(f'获取免费激活错误 info {info}')
        else:
            printErrAndDoLog('activeBag', f'获取免费激活错误 code {r.status_code}')
            raise Exception(f'获取免费激活错误 code {r.status_code}')
