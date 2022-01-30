#  学生健康打卡（简单版）

<img src='https://img.shields.io/badge/Version-0.0.4-orange' style='float:left; width:100px'/>

`JnuStuHealth  `模拟滑块实现打卡项目

本项目实现自动打卡建议自备一台**连续不断运行**的服务器，该项目是在**ubuntu**上面实现的。

本项目的设想是必须**开通邮件通**知，因为上去检查下今天打卡没与设计概念**背道而驰**

因为验证码具有短暂的时效性，后改用了**生产者与消费者**模式，**即产即消**！

##  完整版本 😊

最难的地方是破解滑动模块拿到验证`Validata`

在此特别鸣谢小透明的API版本：https://github.com/SO-JNU/stuhealth-validate-server

通过👆版本，你可以在服务器搭建起一台不断运行的服务且可以提供给他人使用

但是打卡一般一天只进行一次，所以我完成了简单版本，且附上了注释。

👇下面是过滑动验证效果图：

<img src="https://dailypic.hengyimonster.top/typora/aim.gif" style="zoom:66%;float:left" />

##  快速部署 🚀

> 特别注意⚠️：
>
> selenium中的谷歌版本存在BUG即chromedriver的无头版本会报错❌
>
> `window.initNECaptcha`会说找不到的问题，但是**火狐**是没问题的。

授权码的获取简单给个链接🔗： https://www.cnblogs.com/kimsbo/p/10671851.html

```bash
# 以 root 身份下
# git下载
$ git clone https://github.com/hengyi666/JnuStuhealth-simple.git

# 进入工作目录配置文件
$ vim ./utils.py # 设置通知邮箱📮以及授权码

# 安装依赖
$ pip install -r requirements.txt

# 如果遇到了安装pycrypto报错（没有直接跳到下一步）
$ pip uninstall pycrypto
$ pip install pycryptodome

# 安装了firefox
$ apt update && apt upgrade # 更新包 
$ apt install firefox

# 安装geckodriver https://github.com/mozilla/geckodriver/releases
$ wget https://github.com/mozilla/geckodriver/releases/download/v0.30.0/geckodriver-v0.30.0-linux64.tar.gz
$ tar -zxvf ./geckodriverxxx  # 解压下来
$ cp ./geckodriver /usr/bin/geckodriver  # 丢到环境中去必要赋予权限

# 写入 账号 密码 邮箱 备注
# 写入邮箱与授权码
# 写入日志记录路径
$ vim dayClock.txt
$ vim utils.py # SEND_EMAIL AUTH_REGISTERED
$ vim app.py # path

# 运行
$ python app.py
```

## 文件结构 📁

```
├── app.py  # 入口运行文件
├── bgImg # 背景图片
│
├── dayClock.txt  # 保存打卡账号密码文件
├── handlePackage.py # 处理发包
├── handleValidate.py # 处理验证码
│
├── log  # 输出日志
│   
├── requirements.txt # 依赖文件
└── utils.py  # 仓库
```

##  定时开启任务 ⏰

```bash
# 开启定时
# 参考链接 https://blog.csdn.net/longgeaisisi/article/details/90477975
$ sudo apt-get install cron
$ crontab -l # 是否安装以及已有任务
$ service cron start # 开启cron
$ crontab -e # 选择3
# 将  1 0 * * * /usr/bin/python /home/ubuntu/clock/app.py  写入注意修改路径
$ service crond restart
# 建议将app文件中的记录日志的路径写为绝对的
```

##  注意事项 ⚠️

1. 当遇到说`webp`·文件不识别的时候： `pip install --upgrade pillow`升级下就好了
2. 当出现`state code 1`时候，在当前目录下打开`geckodriver.log`查看情况进行修复
3. 当`root`用户无法使用，`sudo crontab -u ubuntu -e`为ubuntu用户开启定时任务

> 其他问题请[谷歌](https://www.google.com.hk/)解决～ 代码问题请提交PR或者开Issue
