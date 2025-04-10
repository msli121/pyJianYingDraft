# 系统任务状态
from enum import Enum


class BizPlatformTaskStatusEnum(Enum):
    """业务平台任务状态枚举"""
    Pending = ('pending', '排队中')
    Doing = ('doing', '进行中')
    DoneSuccess = ('done_success', '处理成功')
    DoneFail = ('done_fail', '处理失败')
    NotNeedHandle = ('not_need_handle', '无需处理')
    Deleted = ('deleted', '已删除')

    def __new__(cls, value, desc):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.desc = desc
        return obj

    @property
    def value(self):
        return self._value_

    @classmethod
    def get_members(cls):
        return {e.value: e.desc for e in cls}


class BizPlatformJyTaskTypeEnum(Enum):
    """业务平台任务类型枚举"""
    HouseVideoClip = ('house_video_clip', '房源视频剪辑')
    GoodStoryClip = ('good_story_clip', '好人好事片段剪辑')
    GoodStoryCompleteClip = ('good_story_complete_clip', '好人好事成片剪辑')

    def __new__(cls, value, desc):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.desc = desc
        return obj

    @property
    def value(self):
        return self._value_

    @classmethod
    def get_members(cls):
        return {e.value: e.desc for e in cls}


class BizPlatformTaskPriorityEnum(Enum):
    """任务优先级枚举"""
    HouseVideoClip = (5, '房源视频剪辑')
    GoodStoryClip = (0, '好人好事片段剪辑')
    GoodStoryCompleteClip = (1, '好人好事成片剪辑')

    def __new__(cls, value, desc):
        obj = object.__new__(cls)
        obj._value_ = value
        obj.desc = desc
        return obj

    @property
    def value(self):
        return self._value_

    @classmethod
    def get_members(cls):
        return {e.value: e.desc for e in cls}
