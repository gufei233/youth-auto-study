# 青春浙江-青年大学习自动签到脚本

青春浙江-青年大学习自动签到脚本

## 开始

### 本地运行

1. 安装相关依赖（requirements.txt）
2. 修改配置文件（config.toml）
3.修改邮箱配置（main.py）
4. 启动自动签到（main.py）





## 项目结构

```txt
|   config.toml
|   config.toml.demo
|   main.py
|   profile.toml
|   README.md
|   requirements.txt
|
+---.github
|   \---workflows
|           run.yml
|
\---end
    \---2023_05_23
```



### 配置文件：config.toml

- #### 配置文件模板为config.toml.demo，需要自行重命名为config.toml

```toml
[user.xxx]
openid="oO-xxxxxxxxxxxxxxxxx"
nid=""     # optional
cardNo=""  # optional
email=""  # optional

[user.yyy]
openid="oO-xxxxxxxxxxxxxxxxx"
nid=""     # optional
cardNo=""  # optional
email=""  # optional

```

- [user.xxx]：这里可以自定义字段如user.pqc表示当前签到的用户
- openid：[必须]用户登录凭据，可以通过抓包获取
- nid：非必要，可以为空，只要你之前在微信上登录过
- cardNo：非必要，可以为空，只要你之前在微信上登录过
- email：非必要，用于发送通知



### main.py

- 立即执行的脚本







### profile.toml

- 程序配置信息，包含api地址，小程序id，UA等



### end/

- 截图输出目录，里面的文件夹根据日期分类。
