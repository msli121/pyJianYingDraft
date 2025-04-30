from typing import Optional, Dict, Any, List

from pydantic import BaseModel


# 系统任务输入参数信息
class JyTaskOutputInfo(BaseModel):
    """
    剪映任务输出结果
    """
    # 是否执行执行成功
    success: Optional[bool] = False
    # 任务状态 从 BizPlatformTaskStatusEnum 中枚举
    task_status: Optional[str] = None
    # 处理信息，如果执行失败，是错误信息
    task_message: Optional[str] = None
    # 处理结果：文本内容或字符串结果
    text_content: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        将实例属性转换为字典形式。
        """
        return {
            "success": self.success,
            "task_status": self.task_status,
            "task_message": self.task_message,
            "text_content": self.text_content,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        从字典初始化 SystemTaskInputInfo 对象
        """
        return cls(**data)


class ClipSettings(BaseModel):
    """素材片段的图像调节设置"""
    alpha: Optional[float] = None
    """图像不透明度, 0-1"""
    flip_horizontal: Optional[bool] = None
    """是否水平翻转"""
    flip_vertical: Optional[bool] = None
    """顺时针旋转的**角度**, 可正可负. 默认为0.0."""
    rotation: Optional[float] = None
    """顺时针旋转的**角度**, 可正可负"""
    scale_x: Optional[float] = None
    """水平缩放比例"""
    scale_y: Optional[float] = None
    """垂直缩放比例"""
    transform_x: Optional[float] = None
    """水平位移, 单位为半个画布宽"""
    transform_y: Optional[float] = None
    """垂直位移, 单位为半个画布高"""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alpha": self.alpha,
            "flip_horizontal": self.flip_horizontal,
            "flip_vertical": self.flip_vertical,
            "rotation": self.rotation,
            "scale_x": self.scale_x,
            "scale_y": self.scale_y,
            "transform_x": self.transform_x,
            "transform_y": self.transform_y
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        从字典初始化 GoodStorySegmentInfo 对象
        """
        return cls(**data)


class GoodStorySegmentInfo(BaseModel):
    """
    好故事剪辑片段信息
    """
    type: Optional[str] = None  # 片段类型 从 BizPlatformSegmentTypeEnum 中枚举
    text: Optional[str] = None  # 文本内容
    url: Optional[str] = None  # 片段素材地址
    filename: Optional[str] = None  # 文件名称
    start_time_ms: Optional[int] = None  # 片段开始时间，毫秒
    duration_ms: Optional[int] = None  # 持续时长,单位毫秒
    local_file_path: Optional[str] = None  # 片段本地文件路径
    has_entry_animation: Optional[bool] = False  # 是否有进入动画
    entry_animation_type: Optional[str] = None  # 进入动画类型
    has_transition: Optional[bool] = False  # 是否有转场
    transition_type: Optional[str] = None  # 转场类型
    has_effect: Optional[bool] = False  # 是否有特效
    effect_type: Optional[str] = None  # 特效类型
    volume: Optional[float] = None  # 音量
    clip_settings: Optional[ClipSettings] = None  # 剪辑设置

    def to_dict(self) -> Dict[str, Any]:
        """
        将实例属性转换为字典形式。
        """
        data = {
            "type": self.type,
            "text": self.text,
            "url": self.url,
            "filename": self.filename,
            "start_time_ms": self.start_time_ms,
            "duration_ms": self.duration_ms,
            "local_file_path": self.local_file_path,
            "has_entry_animation": self.has_entry_animation,
            "entry_animation_type": self.entry_animation_type,
            "has_transition": self.has_transition,
            "transition_type": self.transition_type,
            "has_effect": self.has_effect,
            "effect_type": self.effect_type,
            "volume": self.volume,
        }
        if self.clip_settings:
            data["clip_settings"] = self.clip_settings.to_dict()  # 调用 clip_settings 的 to_dict
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        从字典初始化 GoodStorySegmentInfo 对象
        """
        # 确保数据中的布尔值和浮点数类型正确
        data["has_entry_animation"] = bool(data.get("has_entry_animation", False))
        data["has_transition"] = bool(data.get("has_transition", False))
        data["has_effect"] = bool(data.get("has_effect", False))

        # 手动处理 clip_settings 反序列化
        if data.get("clip_settings"):
            data["clip_settings"] = ClipSettings.from_dict(data["clip_settings"])

        return cls(**data)


class GoodStoryTrackInfo(BaseModel):
    """
    好故事剪辑轨道信息
    """
    track_type: Optional[str] = None  # 轨道类型 从 BizPlatformTrackTypeEnum 中枚举
    track_name: Optional[str] = None  # 轨道名称
    track_show: Optional[bool] = None  # 轨道是否显示
    track_mute: Optional[bool] = None  # 轨道是否静音
    segments: Optional[List[GoodStorySegmentInfo]] = None  # 片段信息

    def to_dict(self) -> Dict[str, Any]:
        """
        将实例属性转换为字典形式。
        """
        return {
            "track_type": self.track_type,
            "track_name": self.track_name,
            "track_show": self.track_show,
            "track_mute": self.track_mute,
            "segments": [segment.to_dict() for segment in self.segments] if self.segments else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        从字典初始化 GoodStoryTrackInfo 对象
        """
        if data.get("segments"):
            data["segments"] = [GoodStorySegmentInfo.from_dict(segment) for segment in data["segments"]]
        return cls(**data)


class GoodStoryClipReqInfo(BaseModel):
    """
    好故事剪辑输入参数信息
    """
    story_id: Optional[int] = None  # 故事ID (修正了类型注解，从 id 改为 int)
    story_name: Optional[str] = None  # 故事名称
    story_duration_ms: Optional[int] = None  # 故事片段总时长
    cover_url: Optional[str] = None  # 封面图地址
    activity_name: Optional[str] = None  # 活动名称
    tracks: Optional[List[GoodStoryTrackInfo]] = None  # 轨道信息

    def to_dict(self) -> Dict[str, Any]:
        """
        将实例属性转换为字典形式。
        """
        return {
            "story_id": self.story_id,
            "story_name": self.story_name,
            "story_duration_ms": self.story_duration_ms,
            "cover_url": self.cover_url,
            "activity_name": self.activity_name,
            "tracks": [track.to_dict() for track in self.tracks] if self.tracks else [],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        """
        从字典初始化 GoodStoryClipInputInfo 对象
        """
        if data.get("tracks"):
            data["tracks"] = [GoodStoryTrackInfo.from_dict(track) for track in data["tracks"]]
        return cls(**data)
