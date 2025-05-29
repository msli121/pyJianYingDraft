import json
import logging
import requests
import concurrent.futures
import os
from datetime import datetime
from typing import Dict, Any

from app.models.biz import CreativityNotification

logger = logging.getLogger(__name__)


class NotificationService:
    @classmethod
    def process_pending_wechat_notifications(cls):
        """处理待发送的微信通知，一次性处理更多通知以适应低频场景"""
        try:
            # 查询待发送通知的数据，一次处理500条
            batch_size = 500
            filters = {"wechat_notification_status": ("eq", 0)}
            notification_count, notification_infos = CreativityNotification.query_with_filters_and_pagination(
                1, batch_size, filters=filters
            )

            if notification_count == 0:
                logger.info("没有待处理的微信通知")
                return 0

            logger.info(f"发现{notification_count}条待发送微信通知")

            # 使用线程池并行发送通知，最大并发数调整为20
            with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
                # 提交所有任务到线程池
                future_to_notification = {
                    executor.submit(cls._send_wechat_notification, notification): notification
                    for notification in notification_infos
                }

                # 获取结果
                success_count = 0
                for future in concurrent.futures.as_completed(future_to_notification):
                    notification = future_to_notification[future]
                    try:
                        result = future.result()
                        if result:
                            success_count += 1
                    except Exception as e:
                        logger.error(f"发送微信通知失败: notification_id={notification.get('id')}, error={str(e)}", exc_info=True)
                        # 更新状态为发送失败
                        CreativityNotification.update(
                            id=notification.get('id'),
                            wechat_notification_status=2,
                            update_time=datetime.now()
                        )

            logger.info(f"成功发送{success_count}条微信通知")
            return success_count
        except Exception as e:
            logger.error(f"处理微信通知任务失败: {str(e)}", exc_info=True)
            return 0

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
            "moduleCode": "common",
            "contentReplacement": {
                "staff_name": notification.get('staff_name', 'unknown'),
                "round": notification.get('round', ''),
                "note_url": notification.get('note_url', '')
            },
            "receivers": [staff_id]
        }

        # 直接从环境变量获取API URL
        api_url = os.getenv('WECHAT_NOTIFICATION_API_URL')

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