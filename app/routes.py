"""
@File: routes.py
@Description: 路由定义

@Author: lms
@Date: 2025/2/25 11:20
"""
from flask import Blueprint, jsonify, request, current_app

from app.auto_cut import jy_auto_cut_and_export_one_step
from utils.qywx import send_qywx_message

api_blueprint = Blueprint('api', __name__)


@api_blueprint.route('/api/ai-clip/status', methods=['GET'])
def check_status():
    """服务状态检查接口"""
    res = {
        "code": 0,
        "msg": "success",
        "data": None,
    }
    return jsonify(res), 200


@api_blueprint.route('/api/ai-clip/clip-house-video', methods=['POST'])
def jy_auto_cut():
    """剪映自动裁剪"""
    log = current_app.logger
    data = request.get_json(silent=True) or {}
    log.info("[剪映自动裁剪] request data: %s", data)
    task_id = data.get('task_id')
    house_no = data.get("house_no")
    video_script_url = data.get("video_script_url")
    notify_url = data.get("notify_url")
    staff_id = data.get("staff_id")
    nickname = data.get("nickname")
    try:
        if not house_no:
            raise ValueError("缺少房源编号")
        if not video_script_url:
            raise ValueError("缺少视频脚本地址")
        oss_url = jy_auto_cut_and_export_one_step(task_id=task_id, house_no=house_no, video_script_url=video_script_url)
        res = {
            "code": 0,
            "msg": "success",
            "data": {
                "oss_url": oss_url,
            }
        }
        if notify_url:
            message = (f"AI智能剪辑成功！\n"
                       f"任务ID:{task_id}\n"
                       f"房源编号: {house_no}\n"
                       f"员工号:{staff_id}\n"
                       f"昵称:{nickname}\n"
                       f"视频URL: {oss_url}")
            send_qywx_message(message, url=notify_url)
        return jsonify(res), 200
    except Exception as e:
        log.error("[剪映自动裁剪] Error: %s", str(e))
        if notify_url:
            message = (f"AI智能剪辑失败！\n"
                       f"任务ID:{task_id}\n"
                       f"房源编号: {house_no}\n"
                       f"员工号:{staff_id}\n"
                       f"昵称:{nickname}\n"
                       f"错误信息：{str(e)}\n")
            send_qywx_message(message, url=notify_url)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200
