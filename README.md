##  前言：

<img src='https://img.shields.io/badge/Version-1.0.0-orange' style='float:left; width:100px'/>

虽然我已经在源码中写的十分详细了，但是不免存在使用者部署不成功的情况

我就无赖擦了擦我台式的灰(**为了x86架构**)，打包了一个存在`firefox+geckodriver+python3.8`的环境

下面的话只要简单几步(根本不需要知道Docker是什么/怎么用)就能完全复刻。

> 我在台式机测试是完全没有问题的，存在错误/Bug请提交 Issues/Pr，十分感谢

##  提前准备

- Docker/Docker-compose的安装
- 邮件授权码的获取（暂时仅支持QQ）

1. [Ubuntu 18.04上安装和使用Docker](https://www.myfreax.com/how-to-install-and-use-docker-on-ubuntu-18-04/)
2. [Ubuntu 20.04上安装Docker Compose](https://www.myfreax.com/how-to-install-and-use-docker-compose-on-ubuntu-20-04/)
3. [QQ邮箱授权码获取](https://www.cnblogs.com/kimsbo/p/10671851.html)

##  设计理念

> 可以当作如何使用的前言,了解我的思路才能更改使用 <(￣ˇ￣)/

1. 拉下来项目后直接使用`docker-compose pull`会拉取到远程仓库的镜像(大约1G内存)。拉下来一次就好了
2. 如果你嫌网速慢得话：Linux/Ubuntu终端走代理：https://www.hengy1.top/article/3dadfa74.html
3. 如果你没有代理得话： https://fastlink-aff.com/auth/register?code=HengY1Sky （广告）
4. 使用`docker-compose up -d --build`的话会运行内置命令，完毕后容器会EXIT但是不会删除容器
5. 重新使用该容器只需要`docker-compose restart`就可以重启服务，这样得话就可以设置`crontab`服务
6. `crontab`设计思路是在每天得定时且需要指定文件`-f docker-compose.yml`即可以每天定时自动打卡

Eg：`1 0 * * * /usr/bin/docker-compose -f /home/ubuntu/Jxx-Stuhealth/docker-compose.yml restart` 

> `docker-compose`究竟在哪可以使用`whereis docker-compose   `查看
>
> `docker-compose.yml`的路径换成自己的就好了

## 如何使用

> 记得给本项目点个星星✨，如果某天崩了会收到消息尽早解决，到本仓库看最新的镜像

DockerHub 仓库：https://hub.docker.com/repository/docker/hengyisky/daily

```bash
$ git clone https://github.com/HengY1Sky/Jxx-Stuhealth.git
$ cd Jxx-Stuhealth
$ git checkout docker # 切换分支
# 当前目录为：克隆目录
# 编辑dayClock.txt与docker-compose.yaml
$ docker-compose pull # 拉下来对应的镜像
$ docker-compose up -d --build # 后台启动将会自己运行规定命令查看是否成功
# 执行完毕之后呢就会EXIT(使用 docker-compose ps)查看
$ docker-compose rm -f # 删除容器
```

