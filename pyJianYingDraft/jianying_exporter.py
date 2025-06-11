"""剪映自动化控制，主要与自动导出有关"""
import os
import shutil
import time
from enum import Enum
from typing import Optional, Literal, Callable

import uiautomation as uia
import pyautogui

class Export_resolution(Enum):
    """导出分辨率"""
    RES_8K = "8K"
    RES_4K = "4K"
    RES_2K = "2K"
    RES_1080P = "1080P"
    RES_720P = "720P"
    RES_480P = "480P"


class Export_framerate(Enum):
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
            try:
                full_desc: str = control.GetPropertyValue(30159).lower()
                return (target_desc == full_desc) if exact else (target_desc in full_desc)
            except:
                return False

        return matcher

    @staticmethod
    def class_name_matcher(class_name: str, depth: int = 1, exact: bool = False) -> Callable[[uia.Control, int], bool]:
        """根据ClassName查找控件的匹配器"""
        class_name = class_name.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            try:
                curr_class_name: str = control.ClassName.lower()
                return (class_name == curr_class_name) if exact else (class_name in curr_class_name)
            except:
                return False

        return matcher

    @staticmethod
    def wait_for_control(control_finder: Callable, timeout: float = 5.0, interval: float = 0.2) -> bool:
        """等待控件出现，提高查找稳定性"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if control_finder():
                return True
            time.sleep(interval)
        return False

    @staticmethod
    def retry_click(control: uia.Control, max_retries: int = 5, delay: float = 0.5) -> bool:
        """重试点击控件，提高操作稳定性"""
        for i in range(max_retries):
            try:
                if control.Exists(0.5):
                    click_result = control.Click(simulateMove=False)
                    print(f"click_result: {click_result}")
                    if delay > 0:
                        time.sleep(delay)
                    return True
            except Exception as e:
                print(f"点击重试 {i + 1}/{max_retries}: {e}")
                if i < max_retries - 1:
                    time.sleep(0.5)
        return False

    @staticmethod
    def send_esc_key() -> None:
        """发送ESC键"""
        print("按下ESC键")
        pyautogui.press('esc')


class JianyingExporter:
    """剪映控制器"""

    app: uia.WindowControl
    """剪映窗口"""
    app_status: Literal["home", "edit", "pre_export"]

    def __init__(self):
        """初始化剪映控制器, 此时剪映应该处于目录页"""
        pass

    def export_draft(self, draft_name: str, output_path: Optional[str] = None, *,
                     resolution: Optional[Export_resolution] = None,
                     framerate: Optional[Export_framerate] = None,
                     timeout: float = 60) -> None:
        """导出指定的剪映草稿, **目前仅支持剪映6及以下版本**

        **注意: 需要确认有导出草稿的权限(不使用VIP功能或已开通VIP), 否则可能陷入死循环**

        Args:
            draft_name (`str`): 要导出的剪映草稿名称
            output_path (`str`, optional): 导出路径, 支持指向文件夹或直接指向文件, 不指定则使用剪映默认路径.
            resolution (`Export_resolution`, optional): 导出分辨率, 默认不改变剪映导出窗口中的设置.
            framerate (`Export_framerate`, optional): 导出帧率, 默认不改变剪映导出窗口中的设置.
            timeout (`float`, optional): 导出超时时间(秒), 默认为1分钟.

        Raises:
            `DraftNotFound`: 未找到指定名称的剪映草稿
            `AutomationError`: 剪映操作失败
        """
        print(f"开始导出 {draft_name} 至 {output_path}")

        # 获取剪映窗口并切换到主页
        if not self._ensure_window_and_home():
            raise Exception("无法获取剪映窗口或切换到主页")

        # 查找并点击草稿
        if not self._click_draft(draft_name):
            raise Exception(f"未找到名为{draft_name}的剪映草稿")

        # 点击导出按钮进入导出页面
        if not self._enter_export_page():
            raise Exception("无法进入导出页面")

        # 获取原始导出路径
        export_path = self._get_export_path()
        if not export_path:
            raise Exception("无法获取导出路径")

        # 设置导出参数
        self._set_export_settings(resolution, framerate)

        # 开始导出
        if not self._start_export():
            raise Exception("无法开始导出")

        # 等待导出完成
        if not self._wait_export_complete(timeout=120):
            raise Exception(f"导出超时, 时限为120秒")

        # 回到主页
        self._ensure_window_and_home()

        # 移动文件到指定路径
        try:
            print(f"开始移动文件 {export_path} 至 {output_path}")
            shutil.move(export_path, output_path)
        except Exception as e:
            print(f"移动文件失败: {e}")

        print(f"导出 {draft_name} 至 {output_path} 完成")

    def export_draft_in_thread(self, draft_name: str, output_path: Optional[str] = None, timeout: float = 1200) -> bool:
        """在线程中导出指定的剪映草稿"""
        try:
            with uia.UIAutomationInitializerInThread(debug=True):
                self.export_draft(draft_name=draft_name, output_path=output_path, timeout=timeout)
            return True
        except Exception as e:
            print(f"在 export_draft_in_thread 中捕获到异常: {e}")
            return False

    def _ensure_window_and_home(self) -> bool:
        """确保窗口存在并切换到主页"""
        if not self.get_window():
            return False
        return self.switch_to_home()

    def _click_draft(self, draft_name: str) -> bool:
        """点击指定草稿"""

        def find_draft():
            draft_name_text = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher(f"HomePageDraftTitle:{draft_name}", exact=True)
            )
            return draft_name_text.Exists(0)

        if not ControlFinder.wait_for_control(find_draft, timeout=3.0):
            return False

        draft_name_text = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher(f"HomePageDraftTitle:{draft_name}", exact=True)
        )

        draft_btn = draft_name_text.GetParentControl()
        if draft_btn is None:
            return False

        return ControlFinder.retry_click(draft_btn, delay=0.5)

    def _enter_export_page(self) -> bool:
        """进入导出页面"""
        if not self.get_window():
            return False

        def find_export_btn():
            export_btn = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn")
            )
            return export_btn.Exists(0)

        if not ControlFinder.wait_for_control(find_export_btn, timeout=3.0):
            print(f"未找到【导出】按钮")
            return False

        export_btn = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn")
        )

        return ControlFinder.retry_click(export_btn, delay=0.5)

    def _get_export_path(self) -> Optional[str]:
        """获取导出路径"""
        if not self.get_window():
            return None

        def find_export_path():
            export_path_sib = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportPath")
            )
            return export_path_sib.Exists(0)

        if not ControlFinder.wait_for_control(find_export_path, timeout=3.0):
            return None

        try:
            export_path_sib = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportPath")
            )
            export_path_text = export_path_sib.GetSiblingControl(lambda ctrl: True)
            if export_path_text:
                return export_path_text.GetPropertyValue(30159)
        except Exception as e:
            print(f"获取导出路径失败: {e}")

        return None

    def _set_export_settings(self, resolution: Optional[Export_resolution],
                             framerate: Optional[Export_framerate]) -> None:
        """设置导出参数"""

        def find_setting_group():
            setting_group = self.app.GroupControl(
                searchDepth=1,
                Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE")
            )
            return setting_group.Exists(0)

        if not ControlFinder.wait_for_control(find_setting_group, timeout=2.0):
            print("警告: 未找到设置组，跳过参数设置")
            return

        setting_group = self.app.GroupControl(
            searchDepth=1,
            Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE")
        )

        # 设置分辨率
        if resolution is not None:
            self._set_resolution(setting_group, resolution)

        # 设置帧率
        if framerate is not None:
            self._set_framerate(setting_group, framerate)

    def _set_resolution(self, setting_group: uia.Control, resolution: Export_resolution) -> None:
        """设置分辨率"""
        try:
            resolution_btn = setting_group.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportSharpnessInput")
            )

            if not resolution_btn.Exists(1.0):
                print("警告: 未找到分辨率设置按钮")
                return

            if not ControlFinder.retry_click(resolution_btn, delay=0.3):
                print("警告: 无法点击分辨率设置按钮")
                return

            resolution_item = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher(resolution.value)
            )

            if resolution_item.Exists(1.0):
                ControlFinder.retry_click(resolution_item, delay=0.3)
            else:
                print(f"警告: 未找到{resolution.value}分辨率选项")
        except Exception as e:
            print(f"设置分辨率失败: {e}")

    def _set_framerate(self, setting_group: uia.Control, framerate: Export_framerate) -> None:
        """设置帧率"""
        try:
            framerate_btn = setting_group.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("FrameRateInput")
            )

            if not framerate_btn.Exists(1.0):
                print("警告: 未找到帧率设置按钮")
                return

            if not ControlFinder.retry_click(framerate_btn, delay=0.3):
                print("警告: 无法点击帧率设置按钮")
                return

            framerate_item = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher(framerate.value)
            )

            if framerate_item.Exists(1.0):
                ControlFinder.retry_click(framerate_item, delay=0.3)
            else:
                print(f"警告: 未找到{framerate.value}帧率选项")
        except Exception as e:
            print(f"设置帧率失败: {e}")

    def _start_export(self) -> bool:
        """开始导出"""

        def find_export_btn():
            export_btn = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True)
            )
            return export_btn.Exists(0)

        if not ControlFinder.wait_for_control(find_export_btn, timeout=2.0):
            return False

        export_btn = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True)
        )

        return ControlFinder.retry_click(export_btn, delay=1.0)

    def _wait_export_complete(self, timeout: float) -> bool:
        """等待导出完成"""
        start_time = time.time()
        check_interval = 1.0  # 增加检查间隔，减少CPU占用

        while time.time() - start_time < timeout:
            if not self.get_window():
                time.sleep(check_interval)
                continue

            if self.app_status != "pre_export":
                time.sleep(check_interval)
                continue

            succeed_close_btn = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportSucceedCloseBtn")
            )

            if succeed_close_btn.Exists(0):
                # ControlFinder.retry_click(succeed_close_btn, delay=0.5)
                ControlFinder.send_esc_key()
                time.sleep(0.5)
                # 编辑状态
                self.app_status = 'edit'
                return True

            time.sleep(check_interval)

        # 超时，回到编辑状态
        ControlFinder.send_esc_key()
        time.sleep(0.5)
        # 编辑状态
        self.app_status = 'edit'
        return False

    def switch_to_home(self) -> bool:
        """切换到剪映主页"""
        if self.app_status == "home":
            return True

        if self.app_status != "edit":
            # print("警告: 当前不在编辑模式，无法切换到主页")
            print("警告: 当前不在编辑模式，通过ESC回到编辑模型")
            ControlFinder.send_esc_key()
            time.sleep(0.5)
            self.app_status = 'edit'

        try:
            close_btn = self.app.GroupControl(searchDepth=1, ClassName="TitleBarButton", foundIndex=3)
            if close_btn.Exists(1.0):
                ControlFinder.retry_click(close_btn, delay=0.5)
                return self.get_window()
        except Exception as e:
            print(f"切换到主页失败: {e}")

        return False

    def get_window(self) -> bool:
        """寻找剪映窗口并置顶"""
        try:
            # 如果已有窗口且存在，先取消置顶
            if hasattr(self, "app") and self.app.Exists(0):
                self.app.SetTopmost(False)

            # 查找剪映窗口
            self.app = uia.WindowControl(searchDepth=1, Compare=self.__jianying_window_cmp)
            if not self.app.Exists(2.0):  # 增加等待时间
                return False

            # 检查导出窗口
            export_window = self.app.WindowControl(searchDepth=1, Name="导出")
            if export_window.Exists(0):
                self.app = export_window
                self.app_status = "pre_export"

            # 激活并置顶窗口
            self.app.SetActive()
            self.app.SetTopmost()
            print(f"获取窗口成功，窗口当前状态：{self.app_status}")
            return True

        except Exception as e:
            print(f"获取窗口失败: {e}")
            return False

    def __jianying_window_cmp(self, control: uia.WindowControl, depth: int) -> bool:
        """剪映窗口比较器"""
        try:
            if control.Name != "剪映专业版":
                return False

            class_name = control.ClassName.lower()
            if "homepage" in class_name:
                self.app_status = "home"
                return True
            elif "mainwindow" in class_name:
                self.app_status = "edit"
                return True

        except Exception as e:
            print(f"窗口比较器异常: {control.Name}, err:{str(e)}")

        return False


if __name__ == '__main__':
    exporter = JianyingExporter()
    draft_name = '自动化剪辑'
    for i in range(100):
        video_save_path = os.path.join('C:\\Users\\Administrator\\Desktop\\自动化剪辑', f"{draft_name}_{i}.mp4")
        start_time = time.time()
        export_success = exporter.export_draft_in_thread(draft_name, video_save_path)
        print(f"导出结果 第{i}个 耗时: {time.time() - start_time:.2f}秒")