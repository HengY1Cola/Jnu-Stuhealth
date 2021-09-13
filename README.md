#  学生健康打卡（简单版）

<img src="https://img.shields.io/badge/%E6%81%92%E6%AF%85-Hengyi-brightgreen" alt="" style=" float:left" />

<img src="https://img.shields.io/badge/Version-0.0.1-orange" alt="" style=" float:left" />

[![build](https://github.com/SO-JNU/stuhealth/workflows/build/badge.svg)](https://github.com/SO-JNU/stuhealth/actions)

Python实现一键打卡。

首先说明该脚本并不会截取你的账号密码

> 在此感谢宸哥支持
>
> 需要完整版请到：
>
> https://github.com/SO-JNU/stuhealth

##  快速部署

```bash
# git下载
$ git clone https://github.com/hengyi666/JnuStuhealth-simple.git
```

##  工作流部署(推荐)

> 根据以下操作，您将在github上每天自动打卡，并不需要其他任何配置
>
> 1. 点击`Fork` 将本仓库拉取到自己那里
> 2. 点击`setting`后设置`Secrets`
>
> ![]()
>
> ![]()

##  本地使用

```bash
# 首次使用需要安装依赖
$ pip3 install -r requirements.txt

# 直接打卡
$ python3 Clock.py -a '你的学号' -p '学号密码'

# 启用打卡消息通知
$ python3 Clock.py -a '你的学号' -p '学号密码' -e '你的邮件'
```

## 参数说明

| 参数         | 简写 | 说明         |
| ------------ | ---- | :----------- |
| `--account`  | `-a` | 学号         |
| `--password` | `-p` | 密码         |
| `--email`    | `-e` | 通知邮件地址 |

##  如何开启邮件通知

> 1. 在这里给个教程 拿到授权码即可（默认是QQ） https://www.cnblogs.com/kimsbo/p/10671851.html
> 2. 然后编辑`clock.py`找到`send_email` 和`auth_registered`分别填入你的邮箱和拿到的授权码
> 3. 如果不是QQ邮箱，请到`Clock_info.py`的`send`的方法下更改对应的配置即可

![指导](https://github.com/hengyi666/JnuStuhealth-simple/blob/main/%E6%88%AA%E5%9B%BE.png?raw=true)

##  注意事项

1. 如果任然报错为某个模块没有找到，请收到安装该模块！

   > 特别的：
   >
   > 当报错为Crypto不存在时，请在终端输入：
   >
   > ```
   > python3 -c "from distutils.sysconfig import get_python_lib;print(get_python_lib())"
   > ```
   >
   > 到该目录下将`Crypto`更改为`Crypyo` 即是大写

2. 可以将以上命令打包为shell脚本，定时执行即可。

   ```bash
   #!/bin/bash
   python3 Clock.py -a xxxx -p xxxxx -e xxx
   ```

   ```bash
   # 授权
   $ chmod +x ./script.sh
   # 执行
   $ ./script.sh
   ```

   
