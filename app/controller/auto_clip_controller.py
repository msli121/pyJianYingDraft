"""
@File: auto_clip_controller.py
@Description: 路由定义

@Author: lms
@Date: 2025/2/25 11:20
"""
import json
import logging

from flask import Blueprint, jsonify, request

from app.entity.jy_task import GoodStoryClipReqInfo
from app.enum.biz import BizPlatformTaskStatusEnum, BizPlatformJyTaskTypeEnum, BizPlatformJyTaskPriorityEnum
from app.models.biz import BizPlatformJyTask
from app.service.good_story_clip_service import GoodStoryClipService
from app.service.house_video_clip_service import handle_auto_clip_house_video
from app.service.task_service import TaskService
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


@api_blueprint.route('/api/ai-clip/query-task-info', methods=['GET', 'POST'])
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
def auto_cut_house_video_route():
    """执行房源视频剪辑"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[执行房源视频剪辑] request data: %s", json.dumps(data, ensure_ascii=False))
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{data.get('task_id')}_{BizPlatformJyTaskTypeEnum.HouseVideoClip.desc}_{data.get('house_no')}",
            task_type=BizPlatformJyTaskTypeEnum.HouseVideoClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Doing.value,
            task_priority=BizPlatformJyTaskPriorityEnum.HouseVideoClip.value,
        )
        task_output = handle_auto_clip_house_video(data)
        if task_output.success:
            # 执行成功
            TaskService.success_task(jy_task_info.get('id'), task_output.text_content)
            res_data = {
                "url": task_output.text_content,
            }
            return jsonify(success_response(res_data)), 200
        else:
            # 执行失败
            TaskService.fail_task(jy_task_info.get('id'), task_output.task_message)
            return jsonify(error_response(task_output.task_message)), 200
    except Exception as e:
        logger.error("[执行房源视频剪辑] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/async-clip-house-video', methods=['POST'])
def async_auto_cut_house_video_route():
    """异步自动剪辑房源视频"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[自动裁剪房源视频] request data: %s", json.dumps(data, ensure_ascii=False))
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
            task_priority=BizPlatformJyTaskPriorityEnum.HouseVideoClip.value,
        )
        res = {
            "jy_task_id": jy_task_info.get('id'),
            "task_status": BizPlatformTaskStatusEnum.Pending.desc
        }
        return jsonify(success_response(res)), 200
    except Exception as e:
        logger.error("[异步自动裁剪房源视频] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/good-story-clip', methods=['POST'])
def good_story_clip_route():
    """执行好人好事片段剪辑"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[执行好人好事片段剪辑] request data: %s", json.dumps(data, ensure_ascii=False))
        story_id = data.get('story_id')
        tracks = data.get("tracks")
        if not story_id:
            raise ValueError("缺少故事ID")
        if not tracks or len(tracks) == 0:
            raise ValueError("缺少轨道信息")
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{story_id}_{BizPlatformJyTaskTypeEnum.GoodStoryClip.desc}",
            task_type=BizPlatformJyTaskTypeEnum.GoodStoryClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Doing.value,
            task_priority=BizPlatformJyTaskPriorityEnum.GoodStoryClip.value,
        )
        req_data = GoodStoryClipReqInfo.from_dict(data)
        task_output = GoodStoryClipService.generate_good_story_clip_one_step(req_data)
        if task_output.success:
            TaskService.success_task(jy_task_info.get('id'), task_output.text_content)
            return jsonify(success_response(task_output.text_content)), 200
        else:
            TaskService.fail_task(jy_task_info.get('id'), task_output.task_message)
            return jsonify(error_response(str(task_output.task_message))), 200
    except Exception as e:
        logger.error("[执行好人好事片段剪辑] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/async-good-story-clip', methods=['POST'])
def async_good_story_clip_route():
    """异步执行好人好事片段剪辑"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[异步执行好人好事片段剪辑] request data: %s", json.dumps(data, ensure_ascii=False))
        story_id = data.get('story_id')
        tracks = data.get("tracks")
        if not story_id:
            raise ValueError("缺少故事ID")
        if not tracks or len(tracks) == 0:
            raise ValueError("缺少轨道信息")
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{story_id}_{BizPlatformJyTaskTypeEnum.GoodStoryClip.desc}",
            task_type=BizPlatformJyTaskTypeEnum.GoodStoryClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Pending.value,
            task_priority=BizPlatformJyTaskPriorityEnum.GoodStoryClip.value,
        )
        res = {
            "jy_task_id": jy_task_info.get('id'),
            "task_status": BizPlatformTaskStatusEnum.Pending.desc
        }
        return jsonify(success_response(res)), 200
    except Exception as e:
        logger.error("[异步执行好人好事片段剪辑] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/activity-video-clip', methods=['POST'])
def activity_video_clip_route():
    """执行活动视频剪辑"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[异步执行活动视频剪辑] request data: %s", json.dumps(data, ensure_ascii=False))
        activity_name = data.get('activity_name')
        if not activity_name:
            raise ValueError("缺少活动名")
        tracks = data.get("tracks")
        if not tracks or len(tracks) == 0:
            raise ValueError("缺少轨道信息")
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{activity_name}_{BizPlatformJyTaskTypeEnum.ActivityVideoClip.desc}",
            task_type=BizPlatformJyTaskTypeEnum.ActivityVideoClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Doing.value,
            task_priority=BizPlatformJyTaskPriorityEnum.ActivityVideoClip.value,
        )
        req_data = GoodStoryClipReqInfo.from_dict(data)
        task_output = GoodStoryClipService.generate_activity_video_one_step(req_data)
        if task_output.success:
            TaskService.success_task(jy_task_info.get('id'), task_output.text_content)
            return jsonify(success_response(task_output.text_content)), 200
        else:
            TaskService.fail_task(jy_task_info.get('id'), task_output.task_message)
            return jsonify(error_response(str(task_output.task_message))), 200
    except Exception as e:
        logger.error("[执行活动视频剪辑] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200


@api_blueprint.route('/api/ai-clip/async-activity-video-clip', methods=['POST'])
def async_activity_video_clip_route():
    """异步执行活动视频剪辑"""
    try:
        data = request.get_json(silent=True) or {}
        logger.info("[异步执行活动视频剪辑] request data: %s", json.dumps(data, ensure_ascii=False))
        activity_name = data.get('activity_name')
        if not activity_name:
            raise ValueError("缺少活动名")
        tracks = data.get("tracks")
        if not tracks or len(tracks) == 0:
            raise ValueError("缺少轨道信息")
        jy_task_info = BizPlatformJyTask.create(
            task_name=f"{activity_name}_{BizPlatformJyTaskTypeEnum.ActivityVideoClip.desc}",
            task_type=BizPlatformJyTaskTypeEnum.ActivityVideoClip.value,
            task_param=json.dumps(data, ensure_ascii=False),
            task_status=BizPlatformTaskStatusEnum.Pending.value,
            task_priority=BizPlatformJyTaskPriorityEnum.ActivityVideoClip.value,
        )
        res = {
            "jy_task_id": jy_task_info.get('id'),
            "task_status": BizPlatformTaskStatusEnum.Pending.desc
        }
        return jsonify(success_response(res)), 200
    except Exception as e:
        logger.error("[异步执行活动视频剪辑] Error: %s", str(e), exc_info=True)
        return jsonify({"code": 1, "msg": str(e), "data": None}), 200
