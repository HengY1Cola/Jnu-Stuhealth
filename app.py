import re
import threading
from handlePackage import *
from handleValidate import prepareToken
from utils import *

# todo 入口
print(banner)
print('Source on GitHub: https://github.com/hengyi666/JnuStuhealth-simple\nAuthor: Hengyi')
path = ''
makePrint2File(path=path)

# todo 分析文本
txtPath = os.path.join(CURRENT_PATH, 'dayClock.txt')
allInfo = getTxt(txtPath)
handleList = []
for each in allInfo:
    one, eachList = dict(), each.split(' ')
    if eachList[0] == '#':
        continue
    if len(eachList) < 3:
        raise Exception('文本参数错误')
    if not re.match(r'^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$', eachList[2]):
        raise Exception('邮箱不匹配')
    one['account'], one['password'], one['email'] = eachList[0], eachList[1], eachList[2]
    handleList.append(one)
if len(handleList) == 0:
    raise Exception('无打卡信息')
print("- 处理完共 {} 打卡信息".format(len(handleList)))

# todo 生产Token
producer = threading.Thread(target=prepareToken, args=(handleList,))
producer.start()

# todo 开始消费拿到每位的JnuId并打卡
for x in range(len(handleList)):
    time.sleep(0.5)
    t = threading.Thread(target=threadModel, args=(handleList[x],))
    t.start()

# todo 打卡处理完成 准备邮件通知
time_start = time.time()
while True:
    now = time.time()
    if now - time_start >= (len(handleList) + 1) * 30:
        print("- 超时")
        break
    if TOTAL_QUEUE.qsize() == len(handleList):
        today = datetime.date.today()
        print(f'- 共用时 {int(now - time_start)} 秒')
        if len(SUCCESS) != 0:
            send("打卡成功", f'{str(today)} 打卡成功', SUCCESS, SEND_EMAIL, AUTH_REGISTERED)
            print(f'{str(SUCCESS)} 打卡通知成功')
        if len(REPEAT) != 0:
            print(f'{str(REPEAT)} 重复打卡')
        if len(ERROR) != 0:
            send("打卡失败", f'{str(today)} 打卡失败', ERROR, SEND_EMAIL, AUTH_REGISTERED)
            print(f'{str(ERROR)} 打卡通知成功')
        send("打卡任务完成", f'{str(today)} 打卡任务完成 成功：{str(SUCCESS)}, 失败：{str(ERROR)}, 重复：{str(REPEAT)}',
             SEND_EMAIL, SEND_EMAIL, AUTH_REGISTERED)
        print('- 打卡任务完成')
        break
print("- 主线程结束")