# app/service/task_service.py
import json
import logging
from datetime import datetime, timedelta
from typing import Dict

from flask import current_app

from app.controller.auto_clip_controller import handle_auto_clip_house_video
from app.entity.jy_task import GoodStoryClipReqInfo
from app.enum.biz import BizPlatformTaskStatusEnum, BizPlatformJyTaskTypeEnum
from app.models.biz import BizPlatformJyTask
from app.service.good_story_clip_service import GoodStoryClipService

logger = logging.getLogger(__name__)


class TaskService:
    @classmethod
    def check_timeout_tasks(cls):
        """检查并处理超时任务"""
        try:
            timeout_threshold = datetime.now() - timedelta(
                hours=current_app.config.get('TASK_TIMEOUT_HOURS', 1)
            )
            filters = {
                "task_status": ("eq", BizPlatformTaskStatusEnum.Doing.value),
                "start_time": ("lt", timeout_threshold)
            }
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 100, filters=filters)
            if task_count > 0:
                logger.info(f"发现{task_count}个超时任务，正在标记为失败...")
                for task in task_infos:
                    cls.fail_task(
                        task_id=task.get('id'),
                        message="任务执行超时，强制终止"
                    )
            return task_count
        except Exception as e:
            logger.error(f"检查超时任务发生错误: {str(e)}", exc_info=True)
            return 0

    @classmethod
    def process_next_task(cls):
        """处理下一个待执行任务"""
        try:
            filters = {"task_status": ("eq", BizPlatformTaskStatusEnum.Doing.value)}
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 1, filters=filters)
            if task_count > 0:
                task_info = task_infos[0]
                logger.info(f"当前有任务在执行 task_id:{task_info.get('id')}, task_name:{task_info.get('task_name')}")
                return None
            filters = {"task_status": ("eq", BizPlatformTaskStatusEnum.Pending.value)}
            orders = [
                {"key": "task_priority", "value": "desc"},
                {"key": "create_time", "value": "asc"}
            ]
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 1, filters=filters,
                                                                                         orders=orders)
            if task_count == 0:
                # logger.info(f"没有待执行的任务")
                return None

            task = task_infos[0]
            return cls.process_single_task(task)
        except Exception as e:
            logger.error(f"获取任务失败: {str(e)}", exc_info=True)
            return None

    @classmethod
    def process_single_task(cls, task: Dict):
        """处理单个任务"""
        task_id = task.get('id')
        try:
            # 标记任务正在执行
            cls.mark_task_doing(task_id)

            task_type = task.get('task_type')
            task_param = json.loads(task.get('task_param'))

            if task_type == BizPlatformJyTaskTypeEnum.HouseVideoClip.value:
                return cls._process_house_video_task(task_id, task_param)
            elif task_type == BizPlatformJyTaskTypeEnum.GoodStoryClip.value:
                return cls._process_good_story_clip_task(task_id, task_param)
            raise ValueError(f"不支持的任务类型: {task_type}")
        except Exception as e:
            logger.error(f"任务处理失败 task_id:{task_id}, error:{str(e)}", exc_info=True)
            cls.fail_task(task_id, str(e))
            return False

    @classmethod
    def _process_house_video_task(cls, task_id: int, task_param: dict):
        """处理房源视频剪辑任务"""
        task_output = handle_auto_clip_house_video(task_param)
        # 更新任务状态
        BizPlatformJyTask.update(
            id=task_id,
            task_status=task_output.task_status,
            task_message=task_output.task_message,
            task_result=task_output.text_content,
            end_time=datetime.now()
        )
        return True

    @classmethod
    def _process_good_story_clip_task(cls, task_id: int, task_param: dict):
        """处理好故事视频剪辑任务"""
        req_data = GoodStoryClipReqInfo.from_dict(task_param)
        task_output = GoodStoryClipService.generate_good_story_clip_one_step(req_data)
        # 更新任务状态
        BizPlatformJyTask.update(
            id=task_id,
            task_status=task_output.task_status,
            task_message=task_output.task_message,
            task_result=task_output.text_content,
            end_time=datetime.now()
        )

    @staticmethod
    def mark_task_doing(task_id: int):
        """标记任务为执行中状态"""
        BizPlatformJyTask.update(
            id=task_id,
            task_status=BizPlatformTaskStatusEnum.Doing.value,
            start_time=datetime.now(),
            end_time=None
        )

    @staticmethod
    def fail_task(task_id: int, message: str = ""):
        """标记任务为失败状态"""
        BizPlatformJyTask.update(
            id=task_id,
            task_status=BizPlatformTaskStatusEnum.DoneFail.value,
            task_message=message,
            end_time=datetime.now()
        )

    @staticmethod
    def success_task(task_id: int, task_result: str = ""):
        """标记任务为成功状态"""
        BizPlatformJyTask.update(
            id=task_id,
            task_status=BizPlatformTaskStatusEnum.DoneSuccess.value,
            task_message=BizPlatformTaskStatusEnum.DoneSuccess.desc,
            task_result=task_result,
            end_time=datetime.now()
        )
