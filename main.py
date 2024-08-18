# -*- coding:utf-8 -*-
import time
from functools import wraps
from types import MethodType
import json
import os
import re
from PIL import Image
from typing import Dict, Optional

import requests
import toml
from datetime import datetime

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage


# 图片下载路径
save_img_path = "./end/"

verbose = True

urls = None
wxAppId = None
headers = None


def load_config():
    global urls, wxAppId, headers  # 声明变量为全局变量
    profile = toml.load(
        os.path.dirname(os.path.realpath(__file__)) + "/profile.toml"
    )
    urls = profile["profile"]["url"]
    wxAppId = profile["profile"]["other"]["wxAppId"]
    headers = {
        "User-Agent": profile["profile"]["other"]["UA"],
    }


class TimeoutRetry:
    max_retry = 3

    def __init__(self, func):
        wraps(func)(self)

    def __call__(self, *args, **kwargs):
        retry_count = 0
        while retry_count < self.max_retry:
            try:
                return self.__wrapped__(*args, **kwargs)
            except requests.RequestException:
                print("请求超时，等待 5 秒后重试")
                time.sleep(5)
                retry_count += 1
        raise TimeoutError("重试三次，连接无效，请检查网络")

    def __get__(self, instance, cls):
        if instance is None:
            return self
        else:
            return MethodType(self, instance)


@TimeoutRetry
def getToken(openId: str) -> Optional[str]:
    response = requests.get(
        url=urls["accessToken"],
        params={"appid": wxAppId, "openid": openId},
        headers={},
    )
    accessTokenMatch = re.compile(
        r"(['\"])(?P<accessToken>([A-Z0-9]|-)+)(\1)"
    ).search(response.text)
    if accessTokenMatch is not None:
        accessToken = accessTokenMatch.groupdict()["accessToken"]
        return accessToken


@TimeoutRetry
def getInfo(
        accessToken: str, nid: Optional[str], cardNo: Optional[str]
) -> Optional[Dict[str, str]]:
    infoResponse = requests.get(
        urls["lastInfo"], params={"accessToken": accessToken}, headers=headers
    )
    userInfo = infoResponse.json()["result"]
    if userInfo is None:
        return

    _nid = userInfo["nid"]
    if _nid is None:
        _nid = nid
    _cardNo = userInfo["cardNo"]
    if _cardNo is None:
        _cardNo = cardNo

    if _nid is None or _cardNo is None:
        return None

    courseResponse = requests.get(
        urls["currentCourse"],
        params={"accessToken": accessToken},
        headers=headers,
    )
    classInfo = courseResponse.json()["result"]
    if classInfo is None:
        return
    classId = classInfo["id"]
    faculty = [item["title"] for item in userInfo["nodes"]]

    if verbose:
        print(
            "[**] Course title: " + classInfo["title"],
            "[**] Group info: " + str(faculty) + ", nid: " + _nid,
            "[**] cardNo: " + _cardNo,
            sep="\n",
        )
    return {"course": classId, "nid": _nid, "cardNo": _cardNo}


@TimeoutRetry
def getUserScore(accessToken: str) -> str:
    return requests.get(
        url=urls["userInfo"],
        params={"accessToken": accessToken},
        headers=headers,
    ).json()["result"]["score"]


@TimeoutRetry
def join(accessToken: str, joinData: Dict[str, str]) -> bool:
    response = requests.post(
        urls["join"],
        params={"accessToken": accessToken},
        data=json.dumps(joinData),
        headers=headers,
    )
    content = response.json()

    if content["status"] == 200:
        print("[*] Check in success")
        return True
    else:
        print("[!] Error:", content["message"])
        return False


@TimeoutRetry
def download_images(accessToken: str, name: str) -> bool:
    now = datetime.now()
    formatted_date = now.strftime("%Y-%m-%d")
    folder_name = formatted_date.replace("-", "_")
    save_folder = os.path.join(save_img_path, folder_name)

    if not os.path.exists(save_folder):
        os.makedirs(save_folder)

    images_info = {
        "end": "end.jpg", 
        "collect_yellow": "collect_yellow.png", 
        "jjh": "jjh.png", 
        "pinfen": "pinfen.png"
    }

    base_url = urls["image"] + accessToken
    response = requests.get(base_url)
    if response.status_code != 200:
        print("Failed to get base URL")
        return False

    for key, filename in images_info.items():
        img_path_list = response.json().get("result").get("uri").split("/")
        img_path_list[-1] = "images"
        img_path_list.append(filename)
        img_url = "/".join(img_path_list)
        img_response = requests.get(img_url)
        if img_response.status_code == 200:
            with open(os.path.join(save_folder, filename), "wb") as f:
                f.write(img_response.content)
                print(f"{filename} saved in {folder_name}")
        else:
            print(f"Failed to download {filename}")

    process_and_overlay_images(save_folder, name, images_info)
    return True


def process_and_overlay_images(save_folder: str, name: str, images_info: dict):
    background = Image.open(os.path.join(save_folder, images_info["end"]))
    jjh = Image.open(os.path.join(save_folder, images_info["jjh"])).resize((int(background.width * 0.346), int(background.height * 0.08)))
    collect_yellow = Image.open(os.path.join(save_folder, images_info["collect_yellow"]))
    pingfen = Image.open(os.path.join(save_folder, images_info["pinfen"])).resize((int(background.width * 0.346), int(background.height * 0.05)))

    background.paste(jjh, (int(background.width * 0.32), int(background.height * 0.86)), jjh)
    background.paste(pingfen, (int(background.width * 0.32), int(background.height * 0.64)), pingfen)

    for i in range(5):
        temp_collect = collect_yellow.resize((int(background.width * 0.1), int(background.height * 0.52 * 0.1)))
        background.paste(temp_collect, (int(background.width * (0.15 + 0.15 * i)), int(background.height * 0.545)), temp_collect)

    final_image_path = os.path.join(save_folder, f"{name}.jpg")
    background.save(final_image_path)
    print(f"Image processed and saved as {final_image_path}")

    for filename in images_info.values():
        os.remove(os.path.join(save_folder, filename))


def runCheckIn(openid: str, nid: Optional[str] = None, cardNo: Optional[str] = None, email: Optional[str] = None, name: Optional[str] = None) -> None:
    # 获取access token
    accessToken = getToken(openid)
    if accessToken is None:
        print("[!] Error getting accessToken, maybe your openid is invalid")
        exit(-1)

    # 获取用户签到数据
    joinData = getInfo(accessToken, nid=nid, cardNo=cardNo)
    if joinData is None:
        print("[!] Error getting join data, maybe your openid is invalid or given nid/cardNo is invalid")
        exit(-1)

    # 显示签到前的用户分数
    print("[*] Score before checkin:", getUserScore(accessToken))

    # 执行签到
    if not join(accessToken, joinData):
        exit(-1)

    # 显示签到后的用户分数
    print("[*] Score after checkin:", getUserScore(accessToken))

    # 下载并处理图片
    if not download_images(accessToken, name):
        print("[!] Error during image download or processing")
        exit(-1)

    # 拼接图片并进行保存
    print("[*] Image processing and saving completed")

    # 如果提供了邮箱，则发送邮件
    if email:
        now = datetime.now()
        formatted_date = now.strftime("%Y-%m-%d")
        folder_name = formatted_date.replace("-", "_")
        final_image_path = os.path.join(save_img_path, folder_name, f"{name}.jpg")
        send_email(email, "Your Check-In Completed", "Here is your confirmation image for the check-in.", final_image_path)

    print("=============================================done=============================================")




def send_email(receiver_email, subject, body, image_path):
    sender_email = ""  # 发件人QQ邮箱地址
    sender_password = ""  # 发件人邮箱授权码/密码

    # 设置SMTP服务器和端口
    smtp_server = "smtp.qq.com" # QQ邮箱
    smtp_port = 465  # SSL端口

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject

    # 添加邮件正文
    msg.attach(MIMEText(body, 'plain'))

    # 添加图片附件
    with open(image_path, 'rb') as file:
        img = MIMEImage(file.read())
        img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(image_path))
        msg.attach(img)

    # 发送邮件
    server = smtplib.SMTP_SSL(smtp_server, smtp_port)  # 使用SSL
    server.login(sender_email, sender_password)
    server.send_message(msg)
    server.quit()
    print(f"Email sent to {receiver_email}")





def main():
    print("[*] Reading openid from config.toml", end="\n\n")
    load_config()

    config = toml.load(
        os.path.dirname(os.path.realpath(__file__)) + "/config.toml"
    )
    for name, user in config["user"].items():
        print("[*] Checking in for openid", name)
        runCheckIn(user["openid"], user["nid"], user["cardNo"], user["email"], name)


if __name__ == "__main__":
    main()
