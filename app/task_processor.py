import logging
import threading
from datetime import datetime, timedelta
from typing import Optional

from flask import current_app

from app.enum.biz import BizPlatformTaskStatusEnum, BizPlatformJyTaskTypeEnum
from app.models.biz import BizPlatformJyTask
from app.controller.auto_clip_controller import handle_auto_clip_house_video

logger = logging.getLogger(__name__)


class TaskProcessor:
    """任务处理器"""

    def __init__(self, app):
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.app = app
        self.running = False  # 新增running变量

    def start(self):
        """启动任务处理器"""
        if self._thread is not None and self._thread.is_alive():
            logger.warning("任务处理器已经在运行中")
            return

        # # 启动前清理遗留的正在执行的任务
        # with self.app.app_context():
        #     doing_tasks = BizPlatformJyTask.query.filter_by(
        #         task_status=BizPlatformTaskStatusEnum.Doing.value
        #     ).all()
        #     for task in doing_tasks:
        #         BizPlatformJyTask.update(
        #             id=task.id,
        #             task_status=BizPlatformTaskStatusEnum.DoneFail.value,
        #             task_message="系统重启导致任务终止",
        #             end_time=datetime.now(),
        #         )
        #     logger.info(f"已清理{len(doing_tasks)}个遗留的正在执行的任务")

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
                with self.app.app_context():
                    interval = self.app.config.get('TASK_LOOP_INTERVAL', 10)
                    self._stop_event.wait(interval)
                    self._check_timeout_tasks()  # 每次循环检查超时任务
                    if not self.running:
                        self._process_next_task()
            except Exception as e:
                logger.error(f"任务处理循环发生错误: {str(e)}", exc_info=True)
                self._stop_event.wait(10)

    def _check_timeout_tasks(self):
        """检查并处理超时任务"""
        try:
            # 查找执行超过1小时的正在执行的任务
            timeout_threshold = datetime.now() - timedelta(hours=1)
            filters = {
                "task_status": ("eq", BizPlatformTaskStatusEnum.Doing.value),
                "start_time": ("lt", timeout_threshold)
            }
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 100, filters=filters)
            if task_count > 0:
                logger.info(f"发现{task_count}个超时任务，正在标记为失败...")
                for task in task_infos:
                    BizPlatformJyTask.update(
                        id=task.get('id'),
                        task_status=BizPlatformTaskStatusEnum.DoneFail.value,
                        task_message="任务执行超时，强制终止",
                        end_time=datetime.now()
                    )
        except Exception as e:
            logger.error(f"检查超时任务发生错误: {str(e)}", exc_info=True)

    def _process_next_task(self):
        """获取并处理下一个待执行任务"""
        try:
            # 查找最高优先级的待执行任务
            filters = {"task_status": ("eq", BizPlatformTaskStatusEnum.Pending.value)}
            orders = [
                {"key": "task_priority", "value": "desc"},
                {"key": "create_time", "value": "asc"}
            ]
            task_count, task_infos = BizPlatformJyTask.query_with_filters_and_pagination(1, 1, filters=filters, orders=orders)
            if task_count == 0:
                return

            task = task_infos[0]
            self.running = True
            try:
                self._process_single_task(task)
            finally:
                self.running = False
        except Exception as e:
            logger.error(f"处理任务失败: {str(e)}", exc_info=True)
            self.running = False

    def _process_single_task(self, task: dict):
        """处理单个任务"""
        task_id = task.get('id')
        task_name = task.get('task_name')
        logger.info(f"开始处理任务 task_id: {task_id}, task_name: {task_name}")

        try:
            # 标记任务为执行中
            BizPlatformJyTask.update(
                id=task_id,
                task_status=BizPlatformTaskStatusEnum.Doing.value,
                start_time=datetime.now(),
                end_time=None
            )

            # 解析任务参数并处理
            task_param = task.get('task_param')
            if not task_param:
                raise ValueError("任务参数为空")

            task_type = task.get('task_type')
            if task_type == BizPlatformJyTaskTypeEnum.HouseVideoClip.value:
                output_info = handle_auto_clip_house_video(task_param)
                BizPlatformJyTask.update(
                    id=task_id,
                    task_status=output_info.task_status,
                    task_message=output_info.task_message,
                    task_result=output_info.text_content,
                    end_time=datetime.now()
                )
            else:
                raise ValueError(f"不支持的任务类型: {task_type}")

            logger.info(f"任务处理完成 task_id: {task_id}, task_name: {task_name}")
        except Exception as e:
            logger.error(f"任务处理失败 task_id: {task_id}, 错误信息: {str(e)}", exc_info=True)
            BizPlatformJyTask.update(
                id=task_id,
                task_status=BizPlatformTaskStatusEnum.DoneFail.value,
                task_message=str(e),
                end_time=datetime.now()
            )