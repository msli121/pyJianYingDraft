from typing import Optional

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

    def to_dict(self):
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
    def from_dict(cls, data: dict):
        """
        从字典初始化 SystemTaskInputInfo 对象
        """
        return cls(**data)
