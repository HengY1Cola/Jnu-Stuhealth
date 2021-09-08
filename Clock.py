import argparse
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import re
from Clock_info import *

print(banner)
print('Source on GitHub: https://github.com/hengyi666/Exhausted-spider\nAuthor: Hengyi')
parser = argparse.ArgumentParser(
    description='This is a tool for searching keywords to find specified urls'
)
parser.add_argument(
    '-a',
    '--account',
    required=True,
    type=str,
    help='The Jnu Account is needed'
)
parser.add_argument(
    '-p',
    '--password',
    required=True,
    type=str,
    help='The Jnu Password is needed'
)
parser.add_argument(
    '-e',
    '--email',
    required=True,
    type=str,
    help='The result will inform you through the email'
)
args = parser.parse_args()

if not re.match(r'^[0-9a-zA-Z_]{0,19}@[0-9a-zA-Z]{1,13}\.[com,cn,net]{1,3}$', args.email):
    raise Exception('Please Input Correct Email')

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
try:
    jnuid = s.post(
        'https://stuhealth.jnu.edu.cn/api/user/login',
        json.dumps({
            'username': args.account,
            'password': base64.b64encode(cipher.encrypt(pad(args.password.encode(), 16))).decode(),
        }),
        headers=header
    ).json()['data']['jnuid']
except Exception as ex:
    raise Exception('Failed to get JNUID')

print('- Congratulations！ your account password is correct')
print(f'- Have got the JnuId: {jnuid}')

bag = checkin(jnuid)
print(f'- Have got the latest Bag')

res = post_bag(bag)

if res['code'] == 0:
    print(f'- Status：Success')
    send('打卡成功', res['msg'], args.email)
elif res['code'] == 1:
    print(f'- Status：Repeat')
    send('重复打卡', res['msg'], args.email)
else:
    print(f'- Status：Error')
    send('打卡失败', '请联系作者：2911567026@qq.com', args.email)

print(f'- Have send the Email to inform you')


