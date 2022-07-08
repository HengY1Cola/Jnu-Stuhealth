import threading
import time
from handleValidate import Chef
from handlePackage import ConsumerWork
from utils import *

print(banner)
print('Source on GitHub: https://github.com/HengY1Sky/Jnu-Stuhealth\nAuthor: Hengyi')

email_validator, user_list_info = ParseHandle().doParse()

for each_info in user_list_info:
    t = threading.Thread(target=ConsumerWork, args=(each_info, True, ))
    t.start()

producer = threading.Thread(target=Chef(user_list_info).prepareToken)
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
            t = threading.Thread(target=ConsumerWork, args=(each_info, False,))
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
