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
from handleGaps import Gaps

# 已知图片的Hash方便与即将填补的图片的hash进行比对
IMG_BG_With_HASH = tuple(
    (i, getImageHash(i)) for i in (Image.open(f'{BG_IMG_PATH}/{j}') for j in os.listdir(BG_IMG_PATH)))


class Chef:
    def __init__(self, user_list, env, platform):
        self.all_list = user_list
        options = webdriver.FirefoxOptions()
        if env == 'pro':
            options.add_argument("--headless")
        profile = webdriver.FirefoxProfile()
        if platform == 'mac':
            executable_path = os.path.join(BIN_DRIVER, 'geckodriver_mac')
        elif platform == "windows":
            executable_path = os.path.join(BIN_DRIVER, 'geckodriver_windows.exe')
        else:
            executable_path = os.path.join(BIN_DRIVER, 'geckodriver_linux')
        BROWSER = webdriver.Firefox(executable_path=executable_path, options=options, firefox_profile=profile)
        BROWSER.install_addon(os.path.realpath('hideHeader'), temporary=True)
        self.browser = BROWSER

    def prepareToken(self, token):
        printInfoAndDoLog("prepareToken", "即将开启浏览器准备获取ValidateToken")
        self.browser.get('https://stuhealth.jnu.edu.cn/jnu_authentication/public/error')
        printInfoAndDoLog("prepareToken", f"即将JNU_AUTH_VERIFY_TOKEN {token} 添加")
        self.browser.add_cookie({
            'name': 'JNU_AUTH_VERIFY_TOKEN',
            'value': token,
            'path': '/',
            'domain': '.jnu.edu.cn',
        })
        time.sleep(5)
        self.browser.get('https://stuhealth.jnu.edu.cn/')
        retry_time, all_times, start = 0, 0, time.time()
        while len(ERR_PWD) + len(SUCCESS) + len(REPEAT) + len(FINAL_ERROR) != len(self.all_list):
            if time.time() - start >= (len(self.all_list) + 2) * 30:
                printErrAndDoLog("prepareToken", "子进程浏览器强制退出")
                raise Exception("强制结束")
            if retry_time >= 3:
                printErrAndDoLog("prepareToken", "超过最大次数")
                break
            try:
                printInfoAndDoLog("prepareToken", '正在获取第 {} 条 ValidateToken'.format(all_times + 1))
                time.sleep(random.randint(2, 4))
                validate = self.getValidateToken() # 切换回滑动模块
                if validate is not None:
                    printInfoAndDoLog("prepareToken", '获取到第 {} 条 ValidateToken'.format(all_times + 1))
                    TOKEN_QUEUE.put(validate)
                else:
                    retry_time += 1
                all_times += 1
                self.browser.get('https://stuhealth.jnu.edu.cn/')
            except Exception as e:
                printErrAndDoLog("prepareToken", e)
                retry_time += 1
        self.browser.quit()
        printInfoAndDoLog("prepareToken", "浏览器线程退出")

    # 滑动模块废弃 2022-11-23 恢复
    def getValidateToken(self):
        WebDriverWait(self.browser, 5).until(
            untilFindElement(By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img[src^="https://"]'))

        domYidunImg = self.browser.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img')
        domYidunSlider = self.browser.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_slider')
        domValidate = self.browser.find_element(By.CSS_SELECTOR, '#captcha input.yidun_input[name="NECaptchaValidate"]')

        validate = None
        for i in range(5):
            img = Image.open(
                io.BytesIO(
                    requests.get(domYidunImg.get_attribute('src').replace('@2x', '').replace('@3x', '')).content))
            imgHash = getImageHash(img)  # 拿到图片的dHash
            imgBackground = min(IMG_BG_With_HASH, key=lambda i: getImageHashDiff(imgHash, i[1]))[0]  # 找到匹配的

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
            ac: ActionChains = ActionChains(self.browser, 20).click_and_hold(domYidunSlider).pause(
                random.randint(400, 700) / 1000)
            for i in range(len(targetSeq) - 1):
                ac = ac.move_by_offset(targetSeq[i + 1] - targetSeq[i], 0)
            ac.pause(random.randint(100, 200) / 1000).release().perform()

            try:
                WebDriverWait(self.browser, 2).until(lambda d: domValidate.get_attribute('value'))
            except TimeoutException:
                pass
            validate = domValidate.get_attribute('value')
            if validate:
                break
        return validate

    # 跟@小透明 讨论后拼图模块
    def getPuzzleToken(self):
        self.browser.execute_script('(document.querySelector(\'#captcha .yidun .yidun_bg-img[src^="https://"]\')||{'
                                    '}).src=null;window.initNECaptcha({element:"#captcha",'
                                    'captchaId:"7d856ac2068b41a1b8525f3fffe92d1c",width:"320px",mode:"float"})')
        WebDriverWait(self.browser, 3, .05).until(untilFindElement(
            By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img[src^="https://"]')
        )
        domYidunImg = self.browser.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img')
        domYidunControl = self.browser.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_control')
        domValidate = self.browser.find_element(By.CSS_SELECTOR, '#captcha input.yidun_input[name="NECaptchaValidate"]')

        validate = None
        for i in range(6):
            imgUrl = domYidunImg.get_attribute('src').replace('@2x', '').replace('@3x', '')
            img = Image.open(io.BytesIO(requests.session().get(imgUrl).content))
            # 将图片转换到 HSV 颜色空间并统一 V 通道后，再根据 RGB 通道判断图块之间的 10 条分界线是否为相邻图案
            # 后面会根据此优化算法
            img = img.convert('HSV')
            for x in range(img.width):
                for y in range(img.height):
                    p = list(img.getpixel((x, y)))
                    p[2] = 255
                    img.putpixel((x, y), tuple(p))
            borderH = [False for _ in range(4)]
            borderV = [False for _ in range(6)]
            img = img.convert('RGB')

            for index, (rangeYA, rangeYB, rangeX) in enumerate((
                    (range(80 - 4, 80), range(80, 80 + 4), range(0, 80)),
                    (range(80 - 4, 80), range(80, 80 + 4), range(80, 160)),
                    (range(80 - 4, 80), range(80, 80 + 4), range(160, 240)),
                    (range(80 - 4, 80), range(80, 80 + 4), range(240, 320)),
            )):
                diffPixel = 0
                for x in rangeX:
                    colorSumA = [0, 0, 0]
                    colorSumB = [0, 0, 0]
                    for ya, yb in zip(rangeYA, rangeYB):
                        colorA = img.getpixel((x, ya))
                        colorB = img.getpixel((x, yb))
                        for i in range(3):
                            colorSumA[i] += colorA[i]
                            colorSumB[i] += colorB[i]
                    diffColor = 0
                    for i in range(3):
                        if abs(colorSumA[i] - colorSumB[i]) / 4 > 24:
                            diffColor += 1
                    if diffColor > 1:
                        diffPixel += 1
                borderH[index] = diffPixel > 20

            for index, (rangeXA, rangeXB, rangeY) in enumerate((
                    (range(80 - 4, 80), range(80, 80 + 4), range(0, 80)),
                    (range(160 - 4, 160), range(160, 240 + 4), range(0, 80)),
                    (range(240 - 4, 240), range(240, 240 + 4), range(0, 80)),
                    (range(80 - 4, 80), range(80, 80 + 4), range(80, 160)),
                    (range(160 - 4, 160), range(160, 240 + 4), range(80, 160)),
                    (range(240 - 4, 240), range(240, 240 + 4), range(80, 160)),
            )):
                diffPixel = 0
                for y in rangeY:
                    colorSumA = [0, 0, 0]
                    colorSumB = [0, 0, 0]
                    for xa, xb in zip(rangeXA, rangeXB):
                        colorA = img.getpixel((xa, y))
                        colorB = img.getpixel((xb, y))
                        for i in range(3):
                            colorSumA[i] += colorA[i]
                            colorSumB[i] += colorB[i]
                    diffColor = 0
                    for i in range(3):
                        if abs(colorSumA[i] - colorSumB[i]) / 4 > 24:
                            diffColor += 1
                    if diffColor > 1:
                        diffPixel += 1
                borderV[index] = diffPixel > 20

            blocks = [
                (0, (borderH[0], borderV[0])),
                (1, (borderH[1], borderV[0], borderV[1])),
                (2, (borderH[2], borderV[1], borderV[2])),
                (3, (borderH[3], borderV[2])),
                (4, (borderH[0], borderV[3])),
                (5, (borderH[1], borderV[3], borderV[4])),
                (6, (borderH[2], borderV[4], borderV[5])),
                (7, (borderH[3], borderV[5])),
            ]
            random.shuffle(blocks)
            blocks.sort(key=lambda e: sum(e[1]) / len(e[1]), reverse=True)
            imgFromBlock, imgToBlock = tuple(x[0] for x in blocks[:2])
            blockFrom = f'#captcha .yidun .yidun_bgimg .yidun_inference.yidun_inference--{imgFromBlock}'
            blockTo = f'#captcha .yidun .yidun_bgimg .yidun_inference.yidun_inference--{imgToBlock}'

            domYidunImgFromBlock = self.browser.find_element(By.CSS_SELECTOR, blockFrom)
            domYidunImgToBlock = self.browser.find_element(By.CSS_SELECTOR, blockTo)
            ActionChains(self.browser, 20).move_to_element(domYidunControl).pause(.5).perform()
            moveOffsetX = (domYidunImgToBlock.rect['x'] + random.randint(0, round(domYidunImgToBlock.rect['width']))) - \
                          (domYidunImgFromBlock.rect['x'] + random.randint(0,
                                                                           round(domYidunImgFromBlock.rect['width'])))
            moveOffsetY = (domYidunImgToBlock.rect['y'] + random.randint(0, round(domYidunImgToBlock.rect['height']))) - \
                          (domYidunImgFromBlock.rect['y'] + random.randint(0,
                                                                           round(domYidunImgFromBlock.rect['height'])))
            ActionChains(self.browser, round(50 + .5 * (moveOffsetX ** 2 + moveOffsetY ** 2) ** .5)). \
                drag_and_drop_by_offset(domYidunImgFromBlock, moveOffsetX, moveOffsetY).perform()

            try:
                WebDriverWait(self.browser, 2).until(lambda d: domValidate.get_attribute('value'))
            except TimeoutException:
                pass
            validate = domValidate.get_attribute('value')
            if validate:
                break
        return validate

    # 采用新的遗传算法后：
    def getGapsToken(self):
        self.browser.execute_script('(document.querySelector(\'#captcha .yidun .yidun_bg-img[src^="https://"]\')||{'
                                    '}).src=null;window.initNECaptcha({element:"#captcha",'
                                    'captchaId:"7d856ac2068b41a1b8525f3fffe92d1c",width:"320px",mode:"float"})')
        WebDriverWait(self.browser, 3, .05).until(untilFindElement(
            By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img[src^="https://"]')
        )
        domYidunImg = self.browser.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_bg-img')
        domYidunControl = self.browser.find_element(By.CSS_SELECTOR, '#captcha .yidun .yidun_control')
        domValidate = self.browser.find_element(By.CSS_SELECTOR, '#captcha input.yidun_input[name="NECaptchaValidate"]')

        validate = None
        for i in range(6):
            imgUrl = domYidunImg.get_attribute('src').replace('@2x', '').replace('@3x', '')
            final = Gaps(imgUrl).run()
            if not final:
                printInfoAndDoLog("prepareToken", f"本次识别失败 准备刷新重试")
                ActionChains(self.browser, 20).move_to_element(domYidunControl).pause(.5).perform()
                python_button = self.browser.find_element(By.CSS_SELECTOR, "#captcha .yidun .yidun_top "
                                                                           ".yidun_top__right .yidun_refresh")
                python_button.click()
                time.sleep(1)
                continue
            blockFrom = f'#captcha .yidun .yidun_bgimg .yidun_inference.yidun_inference--{final[0]}'
            blockTo = f'#captcha .yidun .yidun_bgimg .yidun_inference.yidun_inference--{final[1]}'
            domYidunImgFromBlock = self.browser.find_element(By.CSS_SELECTOR, blockFrom)
            domYidunImgToBlock = self.browser.find_element(By.CSS_SELECTOR, blockTo)
            ActionChains(self.browser, 20).move_to_element(domYidunControl).pause(.5).perform()
            moveOffsetX = (domYidunImgToBlock.rect['x'] + random.randint(0, round(domYidunImgToBlock.rect['width']))) - \
                          (domYidunImgFromBlock.rect['x'] + random.randint(0,
                                                                           round(domYidunImgFromBlock.rect['width'])))
            moveOffsetY = (domYidunImgToBlock.rect['y'] + random.randint(0, round(domYidunImgToBlock.rect['height']))) - \
                          (domYidunImgFromBlock.rect['y'] + random.randint(0,
                                                                           round(domYidunImgFromBlock.rect['height'])))
            ActionChains(self.browser, round(50 + .5 * (moveOffsetX ** 2 + moveOffsetY ** 2) ** .5)). \
                drag_and_drop_by_offset(domYidunImgFromBlock, moveOffsetX, moveOffsetY).perform()
            try:
                WebDriverWait(self.browser, 2).until(lambda d: domValidate.get_attribute('value'))
            except TimeoutException:
                pass
            validate = domValidate.get_attribute('value')
            if validate:
                break
        return validate


if __name__ == "__main__":
    token = "T6JYdHvsmVC06G6BV9e34gbiZZfKhY2tYfwkx6ntbEKTFWOhO5jnor+kzaCHwjAB"
    Chef([1, 2], "dev", "mac").prepareToken(token)
