import re
from handlePackage import *
from utils import *
from handleValidate import prepareToken

# todo 入口
print(banner)
print('Source on GitHub: https://github.com/hengyi666/JnuStuhealth-simple\nAuthor: Hengyi')
makePrint2File(path=os.path.join(CURRENT_PATH, 'log'))

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

# todo 处理Tokens
print("- 即将开启浏览器准备获取ValidateToken")
Tokens = prepareToken(handleList)
if len(Tokens) != len(handleList):
    # 发邮件：模拟验证码拿不到
    send("打卡任务失败", '获取到 {} 个Token,与 {} 个不匹配'.format(len(Tokens), len(handleList)),
         SEND_EMAIL, SEND_EMAIL, AUTH_REGISTERED)
    raise Exception(f'获取到 {len(Tokens)} 个Token,与 {len(handleList)} 个不匹配')
print("- 滑动模块的Token数准备完毕")

# todo 获得对应的JnuId
JnuIdList = []
for x in range(len(handleList)):
    res = getJnuId(handleList[x], Tokens[x])
    if res == '':
        # 发邮件: jnu拿不到了
        send("打卡任务失败", '获取不到JnuId, 可能密码错误，或者脚本失效', SEND_EMAIL, SEND_EMAIL, AUTH_REGISTERED)
        raise Exception('获取不到JnuId, 可能密码错误，或者脚本失效')
    JnuIdList.append(res)

# todo 准备开始打卡
print('- 恭喜完整准备工作，准备发包打卡')
success, error, repeat = [], [], []
for index, each in enumerate(JnuIdList):
    bag = checkin(each)
    print('- 拿到了第 {} 人的昨日数据'.format(index + 1))
    res = post_bag(bag)
    if res['code'] == 0:
        success.append(handleList[index]['email'])
        print('- 第 {} 人打卡成功'.format(index + 1))
    elif res['code'] == 1:
        repeat.append(handleList[index]['email'])
        print('- 第 {} 人重复打卡'.format(index + 1))
    else:
        error.append(handleList[index]['email'])
        print('- 第 {} 人打卡错误'.format(index + 1))

# todo 打卡处理完成 准备邮件通知
today = datetime.date.today()
if len(success) != 0:
    send("打卡成功", f'{str(today)} 打卡成功', success, SEND_EMAIL, AUTH_REGISTERED)
if len(repeat) != 0:
    send("打卡重复", f'{str(today)} 打卡重复', repeat, SEND_EMAIL, AUTH_REGISTERED)
if len(error) != 0:
    send("打卡失败", f'{str(today)} 打卡失败', error, SEND_EMAIL, AUTH_REGISTERED)
send("打卡任务完成", f'{str(today)} 打卡任务完成 成功：{str(success)}, 失败：{str(error)}, 重复：{str(repeat)}',
     SEND_EMAIL, SEND_EMAIL, AUTH_REGISTERED)
