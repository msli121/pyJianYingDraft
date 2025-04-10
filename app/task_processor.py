"""
@File: task_processor.py
@Description: 任务处理器

@Author: lms
@Date: 2025/4/9
"""
import logging
import threading
from datetime import datetime
from typing import Optional

from flask import current_app

from app.enum.biz import BizPlatformTaskStatusEnum, BizPlatformJyTaskTypeEnum
from app.models.biz import BizPlatformJyTask
from app.controller.auto_clip_controller import handle_auto_clip_house_video

logger = logging.getLogger(__name__)


class TaskProcessor:
    """任务处理器"""

    def __init__(self):
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """启动任务处理器"""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("任务处理器已经在运行中")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._process_loop, daemon=True)
        self._thread.start()
        logger.info("任务处理器已启动")

    def stop(self):
        """停止任务处理器"""
        if self._thread is None or not self._thread.is_alive():
            logger.warning("任务处理器未在运行")
            return

        self._stop_event.set()
        self._thread.join()
        self._thread = None
        logger.info("任务处理器已停止")

    def _process_loop(self):
        """任务处理循环"""
        while not self._stop_event.is_set():
            try:
                with current_app.app_context():
                    self._process_pending_tasks()
                    # 使用配置的间隔时间
                    interval = current_app.config.get('TASK_LOOP_INTERVAL', 10)
                    self._stop_event.wait(interval)
            except Exception as e:
                logger.error(f"任务处理循环发生错误: {str(e)}", exc_info=True)
                # 发生错误时等待10秒后继续
                self._stop_event.wait(10)

    def _process_pending_tasks(self):
        """处理待执行的任务"""
        try:
            # 查找待执行的任务
            filters = {
                "task_status": ("eq", BizPlatformTaskStatusEnum.Doing.value),
            }
            # 查找正在执行的任务
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 10, filters=filters)
            if task_count > 0:
                task_ids = ','.join([task.get('id') for task in task_infos])
                logger.info(f"有{task_count}个任务正在执行, 任务ID: {task_ids}")
                for task in task_infos:
                    # 判断任务执行的时间是否大于1小时
                    if (datetime.now() - task.get('start_time')).total_seconds() > 3600:
                        logger.error(f"任务 {task.get('id')}-{task.get('task_name')} 执行时间超过1小时, 强制终止")
                        BizPlatformJyTask.update(id=task.get('id'),
                                                 task_status=BizPlatformTaskStatusEnum.DoneFail.value,
                                                 task_message="任务执行超过1小时，强制终止",
                                                 end_time=datetime.now()
                                                 )
                return

            # 查找待执行的任务
            filters = {
                "task_status": ("eq", BizPlatformTaskStatusEnum.Pending.value),
            }
            orders = [
                {"key": "task_priority", "value": "desc"},
                {"key": "create_time", "value": "asc"}
            ]
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 1, filters=filters,
                                                                                         orders=orders)
            if task_count == 0:
                logger.info("没有待执行的任务~~")
                return
            self._process_single_task(task_infos[0])
        except Exception as e:
            logger.error(f"处理待执行的任务 发生错误: {str(e)}", exc_info=True)

    def _process_single_task(self, task: dict):
        """处理单个任务"""
        task_id = task.get('id')
        task_name = task.get('task_name')
        logger.info(f"开始处理任务 task_id: {task_id}, task_name: {task_name}")
        if not task_id:
            logger.error(f"任务ID为空")
            return
        try:
            # 更新任务状态为执行中
            BizPlatformJyTask.update(id=task_id,
                                     task_status=BizPlatformTaskStatusEnum.Doing.value,
                                     start_time=datetime.now(),
                                     end_time=None)
            # 解析任务参数
            task_param = task.get('task_param')
            if not task_param:
                raise ValueError(f"任务{task_id}参数为空")
            # 根据任务类型调用不同的处理方法
            task_type = task.get('task_type')
            if task_type == BizPlatformJyTaskTypeEnum.HouseVideoClip.value:
                # 处理房源视频剪辑任务
                output_info = handle_auto_clip_house_video(task_param)
                BizPlatformJyTask.update(id=task_id,
                                         task_status=output_info.task_status,
                                         task_message=output_info.task_message,
                                         task_result=output_info.text_content,
                                         end_time=datetime.now(),
                                         )
            else:
                logger.error(f"{task_id}任务类型 {task_type} 不支持")
            logger.info(f"任务处理完成 task_id: {task_id}, task_name: {task_name}")
        except Exception as e:
            logger.error(f"任务 task_id: {task_id}, task_name: {task_name}, 发生错误: {str(e)}", exc_info=True)
            BizPlatformJyTask.update(id=task_id,
                                     task_status=BizPlatformTaskStatusEnum.DoneFail.value,
                                     task_message=str(e),
                                     end_time=datetime.now(),
                                     )


# 全局任务处理器实例
task_processor = TaskProcessor()
