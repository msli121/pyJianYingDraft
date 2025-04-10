"""
@File: qywx_utils.py
@Description: 企业微信消息推送

@Author: lms
@Date: 2025/2/27 16:05
"""

import logging

import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s: %(message)s [in %(filename)s:%(lineno)d]'
)


def send_qywx_message(message, url):
    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": "qyapi.weixin.qq.com",
        "Connection": "keep-alive"
    }
    # 设置请求体
    json_payload = {
        "msgtype": "text",
        "text": {
            "content": message
        }
    }
    try:
        # 执行 POST 请求
        response = requests.post(url, headers=headers, json=json_payload)
        # 获取响应内容
        response_body = response.text
        logging.info(f"{response_body}")
    except Exception as e:
        logging.error(f"企业微信消息推送失败 error:{str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    send_qywx_message("测试消息", "")
