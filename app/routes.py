"""
@File: routes.py
@Description: 路由定义

@Author: lms
@Date: 2025/2/25 11:20
"""
from flask import Blueprint, jsonify, request, current_app

from app.auto_cut import jy_auto_cut_and_export_one_step

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
    try:
        data = request.get_json(silent=True) or {}
        log.info("[剪映自动裁剪] request data: %s", data)
        house_no = data.get("house_no")
        video_script_oss_path = data.get("video_script_oss_path")
        if not house_no:
            raise ValueError("缺少房源编号")
        if not video_script_oss_path:
            raise ValueError("缺少视频脚本OSS路径")
        video_url, local_path = jy_auto_cut_and_export_one_step(house_no, video_script_oss_path)
        res = {
            "code": 0,
            "msg": "success",
            "data": {
                "video_url": video_url,
                "local_path": local_path,
            }
        }
        return jsonify(res), 200
    except Exception as e:
        log.error("[剪映自动裁剪] Error: %s", str(e))
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200
