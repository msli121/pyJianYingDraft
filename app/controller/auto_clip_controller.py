"""
@File: auto_clip_controller.py
@Description: 路由定义

@Author: lms
@Date: 2025/2/25 11:20
"""
import json
import logging

from flask import Blueprint, jsonify, request

from app.entity.jy_task import JyTaskOutputInfo, GoodStoryClipReqInfo
from app.enum.biz import BizPlatformTaskStatusEnum, BizPlatformJyTaskTypeEnum, BizPlatformTaskPriorityEnum
from app.models.biz import BizPlatformJyTask
from app.service.good_story_clip_service import GoodStoryClipService
from app.service.house_video_clip_service import jy_auto_cut_and_export_one_step
from app.utils.qywx_utils import send_qywx_message
from app.utils.response_utils import success_response, error_response

logger = logging.getLogger(__name__)

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


@api_blueprint.route('/api/query-task-info', methods=['GET', 'POST'])
def query_jy_task_info():
    """查询任务详情
    支持GET和POST请求
    请求参数:
        - id: 任务ID
    返回:
        task dict
    """
    try:
        # 获取任务ID
        if request.method == 'GET':
            task_id = request.args.get('id')
        else:
            data = request.get_json(silent=True) or {}
            task_id = data.get('id')
        if not task_id:
            raise ValueError('缺少任务ID参数')
        # 查询任务记录
        task_info = BizPlatformJyTask.get_by_id(task_id)
        if not task_info:
            raise ValueError('任务不存在')
        return jsonify(success_response(task_info)), 200
    except Exception as e:
        logger.error(f"查询任务详情时发生错误: {str(e)}", exc_info=True)
        return jsonify(error_response(str(e))), 200


@api_blueprint.route('/api/ai-clip/clip-house-video', methods=['POST'])
def jy_auto_cut_house_video_route():
    """剪映自动裁剪"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[剪映自动裁剪] request data: %s", json.dumps(data, ensure_ascii=False))
        task_output_info = handle_auto_clip_house_video(data)
        if task_output_info.success:
            return jsonify(success_response({"url": task_output_info.text_content})), 200
        else:
            return jsonify(error_response(str(task_output_info.task_message))), 200
    except Exception as e:
        logger.error("[剪映自动裁剪] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/clip-house-video/sync', methods=['POST'])
def sync_jy_auto_cut_house_video_route():
    """异步自动裁剪房源视频"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[异步自动裁剪房源视频] request data: %s", json.dumps(data, ensure_ascii=False))
        task_id = data.get('task_id')
        house_no = data.get("house_no")
        video_script_url = data.get("video_script_url")
        if not house_no:
            raise ValueError("缺少房源编号")
        if not task_id:
            raise ValueError("缺少任务ID")
        if not video_script_url:
            raise ValueError("缺少视频脚本地址")
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{BizPlatformJyTaskTypeEnum.HouseVideoClip.desc}_{task_id}_{house_no}",
            task_type=BizPlatformJyTaskTypeEnum.HouseVideoClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Pending.value,
            task_priority=BizPlatformTaskPriorityEnum.HouseVideoClip.value,
        )
        res = {
            "jy_task_id": jy_task_info.get('id'),
            "task_status": BizPlatformTaskStatusEnum.Pending.desc
        }
        return jsonify(success_response(res)), 200
    except Exception as e:
        logger.error("[异步自动裁剪房源视频] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/good-story-clip/sync', methods=['POST'])
def sync_good_story_clip_route():
    """异步自动剪辑好事故事片段"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[异步自动剪辑好事故事片段] request data: %s", json.dumps(data, ensure_ascii=False))
        story_id = data.get('story_id')
        tracks = data.get("tracks")
        if not story_id:
            raise ValueError("缺少故事ID")
        if not tracks or len(tracks) == 0:
            raise ValueError("缺少轨道信息")
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{BizPlatformJyTaskTypeEnum.GoodStoryClip.desc}_{story_id}",
            task_type=BizPlatformJyTaskTypeEnum.GoodStoryClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Pending.value,
            task_priority=BizPlatformTaskPriorityEnum.GoodStoryClip.value,
        )
        res = {
            "jy_task_id": jy_task_info.get('id'),
            "task_status": BizPlatformTaskStatusEnum.Pending.desc
        }
        return jsonify(success_response(res)), 200
    except Exception as e:
        logger.error("[异步自动剪辑好事故事片段] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/good-story-clip', methods=['POST'])
def good_story_clip_route():
    """同步自动剪辑好事故事片段"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[同步自动剪辑好事故事片段] request data: %s", json.dumps(data, ensure_ascii=False))
        story_id = data.get('story_id')
        tracks = data.get("tracks")
        if not story_id:
            raise ValueError("缺少故事ID")
        if not tracks or len(tracks) == 0:
            raise ValueError("缺少轨道信息")
        req_data = GoodStoryClipReqInfo.from_dict(data)
        GoodStoryClipService.download_good_story_material(req_data)
        GoodStoryClipService.cut_good_story_clip(req_data)
        local_path = GoodStoryClipService.export_good_story_clip(req_data)
        oss_url = GoodStoryClipService.upload_to_oss(local_path)
        return jsonify(success_response(oss_url)), 200
    except Exception as e:
        logger.error("[同步自动剪辑好事故事片段] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


def handle_auto_clip_house_video(data: dict) -> JyTaskOutputInfo:
    task_id = data.get('task_id')
    house_no = data.get("house_no")
    video_script_url = data.get("video_script_url")
    notify_url = data.get("notify_url")
    staff_id = data.get("staff_id")
    nickname = data.get("nickname")
    output_info = JyTaskOutputInfo()
    try:
        if not house_no:
            raise ValueError("缺少房源编号")
        if not video_script_url:
            raise ValueError("缺少视频脚本地址")
        url = jy_auto_cut_and_export_one_step(task_id=task_id, house_no=house_no, video_script_url=video_script_url)
        if notify_url:
            message = (f"AI智能剪辑成功！\n"
                       f"任务ID:{task_id}\n"
                       f"房源编号: {house_no}\n"
                       f"员工号:{staff_id}\n"
                       f"昵称:{nickname}\n"
                       f"视频URL: {url}")
            send_qywx_message(message, url=notify_url)
        output_info.success = True
        output_info.task_status = BizPlatformTaskStatusEnum.DoneSuccess.value
        output_info.task_message = BizPlatformTaskStatusEnum.DoneSuccess.desc
        output_info.text_content = url
        return output_info
    except Exception as e:
        logger.error("[房源视频自动剪辑] Error: %s", str(e), exc_info=True)
        if notify_url:
            message = (f"AI智能剪辑失败！\n"
                       f"任务ID:{task_id}\n"
                       f"房源编号: {house_no}\n"
                       f"员工号:{staff_id}\n"
                       f"昵称:{nickname}\n"
                       f"错误信息：{str(e)}\n")
            send_qywx_message(message, url=notify_url)
        output_info.success = False
        output_info.task_status = BizPlatformTaskStatusEnum.DoneFail.value
        output_info.task_message = str(e)
        return output_info
