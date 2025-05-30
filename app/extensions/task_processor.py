import logging

from app import scheduler
from app.service.task_service import TaskService
from app.service.notification_service import NotificationService

logger = logging.getLogger(__name__)


def register_scheduled_jobs():
    """注册定时任务"""
    if not scheduler.app:
        return

    # 检查超时任务 - 每分钟执行一次
    scheduler.add_job(
        id='check_timeout_tasks',
        func=check_timeout_tasks,
        trigger='interval',
        seconds=30,
        replace_existing=True,
        max_instances=1,
    )

    # 处理下一个任务
    scheduler.add_job(
        id='process_next_task',
        func=process_next_task,
        trigger='interval',
        seconds=5,
        replace_existing=False,
        max_instances=1,
    )

    # 处理微信通知 - 每10秒执行一次，小数据量高频处理
    scheduler.add_job(
        id='process_wechat_notifications',
        func=process_wechat_notifications,
        trigger='interval',
        seconds=10,  # 每10秒执行一次
        replace_existing=False,
        max_instances=1,
    )

    logger.info("定时任务已注册")


def check_timeout_tasks():
    """检查超时任务"""
    try:
        with scheduler.app.app_context():
            TaskService.check_timeout_tasks()
    except Exception as e:
        logger.error(f"检查超时任务发生错误: {str(e)}", exc_info=True)


def process_next_task():
    """处理下一个任务"""
    try:
        with scheduler.app.app_context():
            TaskService.process_next_task()
    except Exception as e:
        logger.error(f"处理下一个任务发生错误: {str(e)}", exc_info=True)


def process_wechat_notifications():
    """处理微信通知"""
    try:
        with scheduler.app.app_context():
            NotificationService.process_pending_wechat_notifications()
    except Exception as e:
        logger.error(f"处理微信通知发生错误: {str(e)}", exc_info=True)
