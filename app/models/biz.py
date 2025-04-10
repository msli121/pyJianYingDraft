"""
@File: ry_cloud.py
@Description: ry-cloud库的表结构定义

@Author: lms
@Date: 2025/3/6 09:26
"""

from sqlalchemy import Column, DateTime, BigInteger, String, Integer, Text

from app.models.base_model import BaseModel


class BizPlatformJyTask(BaseModel):
    __tablename__ = 'biz_platform_jy_task'

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment='主键')
    task_name = Column(String(255), nullable=True, comment='任务名称')
    task_desc = Column(String(255), nullable=True, comment='任务描述')
    task_param = Column(Text, nullable=True, comment='任务参数')
    task_result = Column(Text, nullable=True, comment='任务结果')
    task_priority = Column(Integer, default=0, comment='任务优先级，越大优先级越高')
    task_type = Column(Text, nullable=True,
                       comment='任务类型，house_video_clip 房源视频剪辑；good_story_clip 好人好事片段剪辑；good_story_complete_clip 好人好事成片剪辑')
    task_status = Column(String(50), nullable=True,
                         comment='任务状态，pending 等待中, doing 执行中；done_success 执行成功；done_fail 执行失败')
    task_message = Column(Text, nullable=True, comment='任务消息')
    start_time = Column(DateTime, default=None, comment='任务开始时间')
    end_time = Column(DateTime, default=None, comment='任务结束时间')
    remark = Column(String(255), nullable=True, comment='备注')
