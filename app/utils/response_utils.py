"""
@File: response_utils.py
@Description: 

@Author: lms
@Date: 2025/3/3 18:21
"""


def success_response(data=None, code=0, msg="success"):
    return {
        "code": code,
        "msg": msg or "success",
        "data": data
    }


def error_response(msg=None, code=1, data=None):
    return {
        "code": code,
        "msg": msg or "处理失败，请重试",
        "data": data
    }
