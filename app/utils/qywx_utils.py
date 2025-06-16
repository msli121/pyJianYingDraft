"""
@File: qywx.py
@Description: 企业微信消息推送

@Author: lms
@Date: 2025/2/27 16:05
"""

import logging

import requests

logger = logging.getLogger(__name__)

# 太屋企业微信 星云助手的业务相关 吉吉国王
TAIWU_WEBHOOK_URL_BUSINESS = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=3fde7210-d944-43d7-8dfb-68613e3d4f6e"

# 太屋企业微信 市场数据视频制作通知 （周末不加班）
TAIWU_MARKET_VIDEO_NOTICE_URL = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=2c003810-8938-468c-a041-f36ca459a85a'


def send_qywx_message(url, message, level="info"):
    """发送企业微信消息
    Args:
        url (str): 企业微信机器人webhook地址
        message (str): 消息内容
        level (str): 消息级别，info 或者 warning, 默认为info
    """
    # 设置请求头
    headers = {
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": "qyapi.weixin.qq.com",
        "Connection": "keep-alive"
    }

    # 根据不同的level设置不同的消息内容
    if level == "info":
        content = f"<font color=\"info\">**📢新信息看看就行**</font>\n{message}"
    elif level == "warning":
        content = f"<font color=\"warning\">**❌出错啦！搞快点！！！**</font>\n{message}"
    else:
        content = message

    # 设置请求体
    json_payload = {
        "msgtype": "markdown",  # 修改为markdown类型
        "markdown": {
            "content": content
        }
    }
    try:
        # 执行POST请求
        response = requests.post(url, headers=headers, json=json_payload)
        # 获取响应内容
        response_body = response.text
        logging.info(f"{response_body}")
    except Exception as e:
        logging.error(f"企业微信消息推送失败 error:{str(e)}", exc_info=True)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
    )
    url = 'https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=3fde7210-d944-43d7-8dfb-68613e3d4f6e'
    message = '测试消息'
    send_qywx_message(url=url, message=message)
