import logging
import requests
import concurrent.futures
import os
from datetime import datetime
from typing import Dict, Any
from flask import current_app

from app import scheduler
from app.models.biz import CreativityNotification

logger = logging.getLogger(__name__)


class NotificationService:
    @classmethod
    def process_pending_wechat_notifications(cls):
        """处理待发送的微信通知，小数据量高频处理"""
        try:
            # 查询待发送通知的数据，一次只处理10条
            batch_size = 10
            filters = {"wechat_notification_status": ("eq", 0)}
            notification_count, notification_infos = CreativityNotification.query_with_filters_and_pagination(
                1, batch_size, filters=filters
            )

            if notification_count == 0:
                # logger.info("没有待处理的微信通知")  # 高频执行时不记录空的情况
                return 0

            logger.info(f"发现{notification_count}条待发送微信通知")

            # 获取应用实例用于传递给线程
            app = scheduler.app
            if not app:
                logger.error("无法获取应用实例，无法处理通知")
                return 0

            # 使用较小的线程池并行发送通知
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # 提交所有任务到线程池，将应用实例传递给每个线程
                future_to_notification = {
                    executor.submit(cls._thread_send_notification, app, notification): notification
                    for notification in notification_infos
                }

                # 获取结果
                success_count = 0
                for future in concurrent.futures.as_completed(future_to_notification):
                    try:
                        result = future.result()
                        if result:
                            success_count += 1
                    except Exception as e:
                        logger.error(f"线程执行异常: {str(e)}", exc_info=True)

            logger.info(f"成功发送{success_count}条微信通知")
            return success_count
        except Exception as e:
            logger.error(f"处理微信通知任务失败: {str(e)}", exc_info=True)
            return 0

    @classmethod
    def _thread_send_notification(cls, app, notification):
        """在线程中推送应用上下文并发送通知"""
        # 在线程中推送应用上下文
        with app.app_context():
            return cls._send_wechat_notification(notification)

    @classmethod
    def _send_wechat_notification(cls, notification: Dict[str, Any]) -> bool:
        """发送单条微信通知"""
        notification_id = notification.get('id')
        staff_id = notification.get('staff_id')

        if not staff_id:
            logger.warning(f"通知缺少员工ID: notification_id={notification_id}")
            CreativityNotification.update(
                id=notification_id,
                wechat_notification_status=2,
                update_time=datetime.now()
            )
            return False

        # 构建请求数据
        payload = {
            "templateCode": "note-placement-notice",
            "msgType": 2,
            "moduleCode": "manager",
            "contentReplacement": {
                "staff_name": notification.get('staff_name', 'unknown'),
                "round": notification.get('round', ''),
                "note_url": notification.get('note_url', '')
            },
            "receivers": [staff_id]
        }

        # 从当前应用上下文获取配置
        api_url = current_app.config.get('WECHAT_NOTIFICATION_API_URL')
        if not api_url:
            # 如果配置中没有，尝试从环境变量获取
            api_url = os.getenv('WECHAT_NOTIFICATION_API_URL',
                     'https://devmanagerapigateway.taiwu.com/manager/api/v1/messages/send')

        # 发送请求
        try:
            headers = {"Content-Type": "application/json"}
            response = requests.post(api_url, json=payload, headers=headers)

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get('code') == 200:
                    # 更新状态为发送成功
                    CreativityNotification.update(
                        id=notification_id,
                        wechat_notification_status=1,
                        update_time=datetime.now()
                    )
                    return True
                else:
                    error_msg = f"API返回错误: {response_data.get('message', '')}"
                    logger.error(f"发送微信通知失败: notification_id={notification_id}, {error_msg}")
                    CreativityNotification.update(
                        id=notification_id,
                        wechat_notification_status=2,
                        update_time=datetime.now()
                    )
                    return False
            else:
                error_msg = f"API请求失败: status_code={response.status_code}"
                logger.error(f"发送微信通知失败: notification_id={notification_id}, {error_msg}")
                CreativityNotification.update(
                    id=notification_id,
                    wechat_notification_status=2,
                    update_time=datetime.now()
                )
                return False
        except Exception as e:
            logger.error(f"发送微信通知请求异常: notification_id={notification_id}, error={str(e)}", exc_info=True)
            CreativityNotification.update(
                id=notification_id,
                wechat_notification_status=2,
                update_time=datetime.now()
            )
            return False