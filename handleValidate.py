import io
import random
import time
import requests
from PIL import ImageChops
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from utils import *


# 已知图片的Hash方便与即将填补的图片的hash进行比对
IMG_BG_With_HASH = tuple(
    (i, getImageHash(i)) for i in (Image.open(f'{BG_IMG_PATH}/{j}') for j in os.listdir(BG_IMG_PATH)))

options = webdriver.FirefoxOptions()
options.headless = True
BROWSER = webdriver.Firefox(options=options)


# 获取验证码的validate token
def getValidateToken():
    # todo 执行脚本
    BROWSER.execute_script(
        '(document.querySelector(\'#captcha .yidun .yidun_bg-img[src^="https://"]\')||{'
        '}).src=null;window.initNECaptcha({element:"#captcha",captchaId:"7d856ac2068b41a1b8525f3fffe92d1c",'
        'width:"320px",mode:"float"})')
    # todo 等待滑动模块的出现
    WebDriverWait(BROWSER, 5).until(untilFindElement(By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img[src^="https://"]'))
    # todo 拿到对应的元素准备拖动
    domYidunImg = BROWSER.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img')
    domYidunSlider = BROWSER.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_slider')
    domValidate = BROWSER.find_element(By.CSS_SELECTOR, '#captcha input.yidun_input[name="NECaptchaValidate"]')

    # 重试3次
    validate = None
    for i in range(3):
        # todo 获取滑动验证码图片并在图库中找到
        img = Image.open(
            io.BytesIO(requests.get(domYidunImg.get_attribute('src').replace('@2x', '').replace('@3x', '')).content))
        imgHash = getImageHash(img)  # 拿到图片的dHash
        imgBackground = min(IMG_BG_With_HASH, key=lambda i: getImageHashDiff(imgHash, i[1]))[0]  # 找到匹配的

        # todo 获取滑动位置
        imgDiff = ImageChops.difference(img, imgBackground).convert('L')  # 通过原图与将要填补的图进行对比
        imgDiffBytes = imgDiff.tobytes()
        targetPosX = 0
        targetPixelCount = 0
        for x in range(imgDiff.width):
            for y in range(imgDiff.height):
                if imgDiffBytes[y * imgDiff.width + x] >= 16:
                    targetPosX += x
                    targetPixelCount += 1
        targetPosX = round(targetPosX / targetPixelCount) - 22
        targetPosX = targetPosX / 260 * 270

        # todo 模拟拖拽
        polynomial = random.choice((
            (0, 7.27419, -23.0881, 40.86, -40.2374, 20.1132, -3.922),
            (0, 11.2642, -54.1671, 135.817, -180.721, 119.879, -31.0721),
            (0, 7.77852, -37.3727, 103.78, -155.152, 115.664, -33.6981),
            (0, 12.603, -61.815, 159.706, -227.619, 166.648, -48.5237),
            (0, 9.94916, -35.3439, 57.2436, -43.3425, 12.4937),
            (0, 8.88576, -29.9556, 49.0498, -39.2717, 12.2918),
            (0, 8.7663, -28.3669, 42.9499, -30.9548, 8.60551),
            (0, 7.36696, -20.605, 27.705, -18.1929, 4.72597),
            (0, -.360233, 15.4068, -36.168, 32.64, -10.5186),
            (0, -.260426, 10.5665, -17.711, 9.70626, -1.30134),
            (0, -.00431368, .131857, 15.3877, -26.4217, 11.9064),
            (0, -.607056, 19.5733, -56.8777, 62.7801, -23.8686),
            (0, 5.84619, -14.9367, 19.8566, -13.293, 3.52692),
        ))
        actionTime = round((500 + targetPosX / 270 * 300 + random.randint(-100, 100)) / 20)
        targetSeq = tuple(
            round(polynomialCalc(x / (actionTime - 1), polynomial) * targetPosX) for x in range(actionTime))
        ac: ActionChains = ActionChains(BROWSER, 20).click_and_hold(domYidunSlider).pause(
            random.randint(400, 700) / 1000)
        for i in range(len(targetSeq) - 1):
            ac = ac.move_by_offset(targetSeq[i + 1] - targetSeq[i], 0)
        ac.pause(random.randint(100, 200) / 1000).release().perform()

        # todo 判断成功了吗？
        try:
            WebDriverWait(BROWSER, 2).until(lambda d: domValidate.get_attribute('value'))
        except TimeoutException:
            pass
        validate = domValidate.get_attribute('value')
        if validate:
            break
    return validate


def prepareToken(PunchList):
    Tokens = []  # 直接放到内存中
    BROWSER.get('https://stuhealth.jnu.edu.cn/')
    reTryTimes = 0
    while len(Tokens) != len(PunchList):
        if reTryTimes >= len(PunchList) + 3:
            break
        reTryTimes += 1
        try:
            length = len(Tokens) + 1
            print('- 正在获取第 {} 条 ValidateToken'.format(length))
            time.sleep(random.randint(5, 10))
            oneValidate = getValidateToken()
            Tokens.append(oneValidate)
            BROWSER.refresh()
        except Exception:
            continue
    BROWSER.quit()
    return Tokens


if __name__ == '__main__':
    oneList = [1, 2, 3]
    res = prepareToken(oneList)
    print(len(res))
