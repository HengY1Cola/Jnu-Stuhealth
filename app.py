import threading
import time
from handleValidate import Chef
from handlePackage import ConsumerWork
from handleIpProxy import IpProxy
from utils import *


print(banner)
print('Source on GitHub: https://github.com/HengY1Sky/Jnu-Stuhealth\nAuthor: Hengyi')

# 加载配置
setting = readSettings()
env = setting.get("env", "linux")
platform = setting.get("platform", "pro")
if not (env == "pro" or env == "dev") or not (platform == "mac" or platform == "linux"):
    raise Exception("No match ENV or PLATFORM. ENV: pro or dev | PLATFORM: mac or linux")

# 处理用户信息
email_validator, user_list_info = ParseHandle().doParse()

# 判断代理时候开启 建议人数都走代理 https://www.zmhttp.com/
proxy = setting.get("proxy", {'switch': 'off'})
switch = proxy['switch']
if switch == "on":
    ipList = IpProxy().GetNumProxy(len(user_list_info))
    printInfoAndDoLog("app", f"获取代理 {len(ipList)} 条")
    for each in ipList:
        PROXY_QUEUE.put(each)
else:
    printInfoAndDoLog("app", "关闭代理模式")


for each_info in user_list_info:
    one = PROXY_QUEUE.get()
    t = threading.Thread(target=ConsumerWork, args=(each_info, True, one, ))
    t.start()

producer = threading.Thread(target=Chef(user_list_info, env, platform).prepareToken)
producer.start()

time_start = time.time()
today = date.today()
while True:
    now = time.time()
    if now - time_start >= (len(user_list_info) + 2) * 30:
        printErrAndDoLog("app", "超时 强制结束")
        raise Exception("强制结束")
    if len(DEAD_LATER) != 0:
        for each_info in DEAD_LATER:
            t = threading.Thread(target=ConsumerWork, args=(each_info, False, "",))
            t.start()
            DEAD_LATER.remove(each_info)
    if len(ERR_PWD) + len(SUCCESS) + len(REPEAT) + len(FINAL_ERROR) == len(user_list_info):
        printInfoAndDoLog("app", f'共用时 {int(now - time_start)} 秒')
        if len(SUCCESS) != 0:
            email_validator.doNotice("打卡成功", SUCCESS, f'{str(today)} 打卡成功')
            printInfoAndDoLog("doNotice", f'{str(SUCCESS)} 打卡通知成功')
        if len(REPEAT) != 0:
            printInfoAndDoLog("doNotice", f'{str(REPEAT)} 重复打卡')
        if len(FINAL_ERROR) != 0:
            email_validator.doNotice("打卡失败", FINAL_ERROR, f'{str(today)} 打卡失败')
            printInfoAndDoLog("doNotice", f'{str(FINAL_ERROR)} 打卡通知失败')
        printInfoAndDoLog("app", f'{str(today)} 打卡任务完成 成功：{str(SUCCESS)}, 失败：{str(FINAL_ERROR)}, 重复：{str(REPEAT)}')
        break
printInfoAndDoLog("app", "主线程结束")
