"""剪映自动化控制，主要与自动导出有关"""
import os
import shutil
import time
import traceback
from enum import Enum
from typing import Optional, Literal, Callable, Union

import uiautomation as uia

from . import exceptions
from .exceptions import AutomationError, DraftNotFound, VersionMismatchError


class ExportResolution(Enum):
    """导出分辨率"""
    RES_8K = "8K"
    RES_4K = "4K"
    RES_2K = "2K"
    RES_1080P = "1080P"
    RES_720P = "720P"
    RES_480P = "480P"


class ExportFramerate(Enum):
    """导出帧率"""
    FR_24 = "24fps"
    FR_25 = "25fps"
    FR_30 = "30fps"
    FR_50 = "50fps"
    FR_60 = "60fps"


class ControlFinder:
    """控件查找器，封装部分与控件查找相关的逻辑"""

    @staticmethod
    def desc_matcher(target_desc: str, depth: int = 2, exact: bool = False) -> Callable[[uia.Control, int], bool]:
        """根据full_description查找控件的匹配器"""
        target_desc = target_desc.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            full_desc: str = control.GetPropertyValue(30159).lower()
            return (target_desc == full_desc) if exact else (target_desc in full_desc)

        return matcher

    @staticmethod
    def class_name_matcher(class_name: str, depth: int = 1, exact: bool = False) -> Callable[[uia.Control, int], bool]:
        """根据ClassName查找控件的匹配器"""
        class_name = class_name.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            curr_class_name: str = control.ClassName.lower()
            return (class_name == curr_class_name) if exact else (class_name in curr_class_name)

        return matcher

    @staticmethod
    def name_matcher(name: str, depth: int = 1, exact: bool = False) -> Callable[[uia.Control, int], bool]:
        """根据Name查找控件的匹配器"""
        name = name.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            curr_name: str = control.Name.lower()
            return (name == curr_name) if exact else (name in curr_name)

        return matcher


class JianyingController:
    """剪映控制器"""

    app: uia.WindowControl
    """剪映窗口"""
    app_status: Literal["home", "edit", "pre_export", "unknown"]
    version: str
    """剪映版本号"""

    def __init__(self, version: str = "6.x"):
        """
        初始化剪映控制器

        Args:
            version: 剪映版本号，默认为6.x
        """
        self.version = version
        self.app_status = "unknown"
        self._validate_version()

    def _validate_version(self) -> None:
        """验证剪映版本是否兼容"""
        supported_versions = ["6.x"]
        if self.version not in supported_versions:
            raise VersionMismatchError(f"当前仅支持以下剪映版本: {', '.join(supported_versions)}")

    def export_draft(self, draft_name: str, output_path: Optional[str] = None, *,
                     resolution: Optional[ExportResolution] = None,
                     framerate: Optional[ExportFramerate] = None,
                     timeout: float = 1200,
                     check_interval: float = 1.0) -> None:
        """导出指定的剪映草稿

        **注意: 需要确认有导出草稿的权限(不使用VIP功能或已开通VIP), 否则可能陷入死循环**

        Args:
            draft_name (`str`): 要导出的剪映草稿名称
            output_path (`str`, optional): 导出路径, 支持指向文件夹或直接指向文件, 不指定则使用剪映默认路径.
            resolution (`ExportResolution`, optional): 导出分辨率, 默认不改变剪映导出窗口中的设置.
            framerate (`ExportFramerate`, optional): 导出帧率, 默认不改变剪映导出窗口中的设置.
            timeout (`float`, optional): 导出超时时间(秒), 默认为20分钟.
            check_interval (`float`, optional): 检查导出状态的间隔时间(秒), 默认为1秒.

        Raises:
            `DraftNotFound`: 未找到指定名称的剪映草稿
            `AutomationError`: 剪映操作失败
            `TimeoutError`: 导出超时
        """
        print(f"开始导出 {draft_name} 至 {output_path}")

        try:
            self.get_window(timeout=10)
            self.switch_to_home()

            # 点击对应草稿
            draft_name_text = self._find_control(
                control_type=uia.TextControl,
                compare=ControlFinder.desc_matcher(f"HomePageDraftTitle:{draft_name}", exact=True),
                search_depth=2,
                timeout=5,
                error_msg=f"未找到名为{draft_name}的剪映草稿"
            )

            draft_btn = draft_name_text.GetParentControl()
            assert draft_btn is not None, "草稿按钮不存在"
            self._safe_click(draft_btn)
            self.get_window(timeout=10)

            # 点击导出按钮
            export_btn = self._find_control(
                control_type=uia.TextControl,
                compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn"),
                search_depth=2,
                timeout=5,
                error_msg="未在编辑窗口中找到导出按钮"
            )
            self._safe_click(export_btn)
            self.get_window(timeout=10)

            # 获取原始导出路径（带后缀名）
            export_path_sib = self._find_control(
                control_type=uia.TextControl,
                compare=ControlFinder.desc_matcher("ExportPath"),
                search_depth=2,
                timeout=5,
                error_msg="未找到导出路径框"
            )

            export_path_text = export_path_sib.GetSiblingControl(lambda ctrl: True)
            assert export_path_text is not None, "导出路径文本控件不存在"
            export_path = export_path_text.GetPropertyValue(30159)

            # 设置分辨率
            if resolution is not None:
                self._set_export_option(
                    option_name="分辨率",
                    option_value=resolution.value,
                    parent_matcher=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"),
                    option_btn_matcher=ControlFinder.desc_matcher("ExportSharpnessInput"),
                    option_item_matcher=lambda value: ControlFinder.desc_matcher(value)
                )

            # 设置帧率
            if framerate is not None:
                self._set_export_option(
                    option_name="帧率",
                    option_value=framerate.value,
                    parent_matcher=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"),
                    option_btn_matcher=ControlFinder.desc_matcher("FrameRateInput"),
                    option_item_matcher=lambda value: ControlFinder.desc_matcher(value)
                )

            # 点击导出
            export_btn = self._find_control(
                control_type=uia.TextControl,
                compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True),
                search_depth=2,
                timeout=5,
                error_msg="未在导出窗口中找到导出按钮"
            )
            self._safe_click(export_btn)

            # 等待导出完成
            self._wait_for_export_complete(timeout, check_interval)

            # 回到目录页
            self.get_window(timeout=10)
            self.switch_to_home()

            # 复制导出的文件到指定目录
            if output_path is not None:
                self._move_exported_file(export_path, output_path)

            print(f"导出 {draft_name} 至 {output_path} 完成")

        except Exception as e:
            print(f"导出过程中发生错误: {e}")
            traceback.print_exc()
            raise

    def _set_export_option(self, option_name: str, option_value: str, parent_matcher: Callable,
                           option_btn_matcher: Callable, option_item_matcher: Callable) -> None:
        """设置导出选项的通用方法"""
        # 查找设置组
        setting_group = self._find_control(
            control_type=uia.GroupControl,
            compare=parent_matcher,
            search_depth=1,
            timeout=5,
            error_msg=f"未找到导出{option_name}设置组"
        )

        # 查找选项按钮
        option_btn = self._find_control(
            control_type=uia.TextControl,
            parent=setting_group,
            compare=option_btn_matcher,
            search_depth=2,
            timeout=3,
            error_msg=f"未找到导出{option_name}下拉框"
        )
        self._safe_click(option_btn)

        # 查找选项值并点击
        option_item = self._find_control(
            control_type=uia.TextControl,
            compare=option_item_matcher(option_value),
            search_depth=2,
            timeout=3,
            error_msg=f"未找到{option_value}{option_name}选项"
        )
        self._safe_click(option_item)

    def _wait_for_export_complete(self, timeout: float, check_interval: float) -> None:
        """等待导出完成"""
        st = time.time()
        while True:
            self.get_window(timeout=5)
            if self.app_status != "pre_export":
                time.sleep(check_interval)
                continue

            succeed_close_btn = self.app.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher("ExportSucceedCloseBtn")
            )

            if succeed_close_btn.Exists(0):
                self._safe_click(succeed_close_btn)
                break

            if time.time() - st > timeout:
                raise TimeoutError(f"导出超时, 时限为{timeout}秒")

            time.sleep(check_interval)

    def _move_exported_file(self, source_path: str, destination_path: str) -> None:
        """移动导出的文件到指定位置"""
        try:
            # 如果目标路径是目录，则使用原文件名
            if os.path.isdir(destination_path) or destination_path.endswith(os.path.sep):
                destination_path = os.path.join(destination_path, os.path.basename(source_path))

            # 确保目标目录存在
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            # 移动文件
            shutil.move(source_path, destination_path)
            print(f"已将文件从 {source_path} 移动至 {destination_path}")
        except Exception as e:
            print(f"移动文件时出错: {e}")
            raise

    def export_draft_in_thread(self, draft_name: str, output_path: Optional[str] = None,
                               timeout: float = 1200, check_interval: float = 1.0) -> bool:
        """在线程中导出指定的剪映草稿"""
        try:
            with uia.UIAutomationInitializerInThread(debug=True):
                self.export_draft(
                    draft_name=draft_name,
                    output_path=output_path,
                    timeout=timeout,
                    check_interval=check_interval
                )
            return True
        except Exception as e:
            print(f"在 export_draft_in_thread 中捕获到异常: {e}")
            traceback.print_exc()
            return False

    def switch_to_home(self) -> None:
        """切换到剪映主页"""
        if self.app_status == "home":
            return
        if self.app_status != "edit":
            raise AutomationError("仅支持从编辑模式切换到主页")

        close_btn = self._find_control(
            control_type=uia.GroupControl,
            compare=ControlFinder.class_name_matcher("TitleBarButton"),
            search_depth=1,
            found_index=3,
            timeout=5,
            error_msg="未找到关闭编辑窗口的按钮"
        )
        self._safe_click(close_btn)
        time.sleep(2)  # 等待窗口切换
        self.get_window(timeout=10)

    def get_window(self, timeout: float = 10) -> None:
        """寻找剪映窗口并置顶"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            # 如果窗口已存在且有效，则尝试置顶
            if hasattr(self, "app") and self.app.Exists(0):
                try:
                    self.app.SetTopmost(False)
                except Exception:
                    pass

            # 查找剪映主窗口
            self.app = uia.WindowControl(searchDepth=1, Compare=self.__jianying_window_cmp)

            if self.app.Exists(0):
                # 检查是否有导出窗口
                export_window = self.app.WindowControl(searchDepth=1, Name="导出")
                if export_window.Exists(0):
                    self.app = export_window
                    self.app_status = "pre_export"

                # 激活并置顶窗口
                self.app.SetActive()
                self.app.SetTopmost()
                return

            time.sleep(1)

        raise AutomationError(f"在{timeout}秒内未找到剪映窗口")

    def _find_control(self, control_type: type, compare: Callable = None, parent: uia.Control = None,
                      search_depth: int = 1, timeout: float = 5, error_msg: str = "未找到控件",
                      found_index: int = 1) -> uia.Control:
        """
        查找UI控件的通用方法，支持超时等待

        Args:
            control_type: 控件类型，如uia.TextControl
            compare: 匹配器函数
            parent: 父控件，默认为None表示从根开始查找
            search_depth: 搜索深度
            timeout: 超时时间（秒）
            error_msg: 未找到控件时的错误消息
            found_index: 查找的控件索引

        Returns:
            找到的控件

        Raises:
            AutomationError: 超时未找到控件
        """
        start_time = time.time()
        target_parent = parent if parent is not None else self.app

        while time.time() - start_time < timeout:
            try:
                control = control_type(
                    searchDepth=search_depth,
                    Compare=compare,
                    parent=target_parent,
                    foundIndex=found_index
                )
                if control.Exists(0):
                    return control
            except Exception:
                pass

            time.sleep(0.5)

        raise AutomationError(error_msg)

    def _safe_click(self, control: uia.Control) -> None:
        """安全点击控件，增加点击成功率"""
        try:
            # 确保控件可见并启用
            if not control.IsEnabled() or not control.IsVisible():
                raise AutomationError(f"控件不可用或不可见: {control.GetPropertyValue(30159)}")

            # 先将鼠标移动到控件上
            control.MoveCursorToMyCenter()
            time.sleep(0.2)

            # 点击控件
            control.Click(simulateMove=False)
            time.sleep(0.5)  # 给UI响应时间
        except Exception as e:
            print(f"点击控件时出错: {e}")
            raise

    def __jianying_window_cmp(self, control: uia.WindowControl, depth: int) -> bool:
        """剪映窗口匹配器"""
        if control.Name != "剪映专业版":
            return False

        class_name = control.ClassName.lower()
        if "homepage".lower() in class_name:
            self.app_status = "home"
            return True
        elif "mainwindow".lower() in class_name:
            self.app_status = "edit"
            return True

        return False