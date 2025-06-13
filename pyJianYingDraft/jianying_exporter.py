"""剪映自动化控制，主要与自动导出有关"""

import os
import random
import shutil
import time
import logging
from enum import Enum
from typing import Optional, Literal, Callable, List

import psutil
import uiautomation as uia
import pyautogui

from app_config import AppConfig

logger = logging.getLogger(__name__)


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
    def desc_matcher(
            target_desc: str, depth: int = 2, exact: bool = False
    ) -> Callable[[uia.Control, int], bool]:
        """根据full_description查找控件的匹配器"""
        target_desc = target_desc.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            try:
                full_desc: str = control.GetPropertyValue(30159).lower()
                return (
                    (target_desc == full_desc) if exact else (target_desc in full_desc)
                )
            except:
                return False

        return matcher

    @staticmethod
    def class_name_matcher(
            class_name: str, depth: int = 1, exact: bool = False
    ) -> Callable[[uia.Control, int], bool]:
        """根据ClassName查找控件的匹配器"""
        class_name = class_name.lower()

        def matcher(control: uia.Control, _depth: int) -> bool:
            if _depth != depth:
                return False
            try:
                curr_class_name: str = control.ClassName.lower()
                return (
                    (class_name == curr_class_name)
                    if exact
                    else (class_name in curr_class_name)
                )
            except:
                return False

        return matcher

    @staticmethod
    def wait_for_control(
            control_finder: Callable, timeout: float = 5.0, interval: float = 0.2
    ) -> bool:
        """等待控件出现，提高查找稳定性"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if control_finder():
                return True
            time.sleep(interval)
        return False

    @staticmethod
    def retry_click(
            control: uia.Control, max_retries: int = 3, delay: float = 0.5
    ) -> bool:
        """重试点击控件，提高操作稳定性"""
        for i in range(max_retries):
            try:
                if control.Exists(0.5):
                    control.Click(simulateMove=False)
                    if delay > 0:
                        time.sleep(delay)
                    return True
            except Exception as e:
                logger.info(f"点击重试 {i + 1}/{max_retries}: {e}")
                if i < max_retries - 1:
                    time.sleep(0.5)
        return False

    @staticmethod
    def retry_click_enhanced(
            control: uia.Control,
            max_retries: int = 3,
            delay: float = 0.5,
            check_focused: bool = True,
            random_offset: bool = True,
            offset_range: int = 3,
    ) -> bool:
        """
        增强版重试点击方法，提高自动化稳定性

        Args:
            control: 目标控件
            max_retries: 最大重试次数
            delay: 每次点击后的等待时间
            check_focused: 点击前尝试聚焦控件
            random_offset: 是否添加随机偏移（防反爬）
            offset_range: 随机偏移的范围（像素）
        """
        for i in range(max_retries):
            try:
                # 1.验证控件状态
                if not control.Exists(0.5):
                    logger.info(f"[控件点击] 控件不存在，重试 {i + 1}/{max_retries}")
                    time.sleep(0.5)
                    continue
                # 2.预处理：聚焦控件（可选）
                if check_focused:
                    control.SetFocus()
                    time.sleep(0.2)
                # 3.计算点击位置（支持随机偏移）
                rect = control.BoundingRectangle
                center_x = rect.left + (rect.width() // 2)
                center_y = rect.top + (rect.height() // 2)
                # 4.添加随机偏移（防反爬机制）
                if random_offset:
                    offset_x = random.randint(-offset_range, offset_range)
                    offset_y = random.randint(-offset_range, offset_range)
                    click_x = center_x + offset_x
                    click_y = center_y + offset_y
                else:
                    click_x, click_y = center_x, center_y
                # 5.直接调用底层API，避免封装层的问题
                uia.Click(click_x, click_y, waitTime=0.1)
                # 6.等待并验证结果
                time.sleep(delay)
                logger.info(f"[控件点击] 点击执行成功")
                return True
            except Exception as e:
                logger.error(f"点击异常，重试 {i + 1}/{max_retries}: {e}", exc_info=True)
            # 重试前等待
            if i < max_retries - 1:
                time.sleep(0.5)
        logger.error("❌ 达到最大重试次数，点击失败")
        return False

    @staticmethod
    def move_and_click(control: uia.Control) -> bool:
        """备用策略：先移动到控件再点击（模拟真实用户）"""
        try:
            rect = control.BoundingRectangle
            center_x = rect.left + (rect.width() // 2)
            center_y = rect.top + (rect.height() // 2)
            # 先移动到控件附近
            uia.MoveTo(center_x - 5, center_y)
            time.sleep(0.1)
            uia.MoveTo(center_x, center_y, 0.5)  # 缓慢移动到中心
            time.sleep(0.1)
            # 点击
            uia.Click(center_x, center_y)
            time.sleep(0.5)
            return True
        except Exception as e:
            logger.error(f"微动点击失败: {e}", exc_info=True)
            return False

    @staticmethod
    def send_esc_key() -> None:
        """发送ESC键"""
        logger.info("按下ESC键")
        pyautogui.press("esc")


class JianyingExporter:
    """剪映控制器"""

    app: uia.WindowControl
    """剪映窗口"""
    app_status: Literal["home", "edit", "pre_export"]

    def __init__(self):
        """初始化剪映控制器, 此时剪映应该处于目录页"""
        pass

    def export_draft(
            self,
            draft_name: str,
            output_path: Optional[str] = None,
            *,
            resolution: Optional[Export_resolution] = None,
            framerate: Optional[Export_framerate] = None,
            timeout: float = 60,
    ) -> bool:
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
        try:

            logger.info(f"开始导出 {draft_name} 至 {output_path}")

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
                logger.info(f"开始移动文件 {export_path} 至 {output_path}")
                shutil.move(export_path, output_path)
            except Exception as e:
                logger.info(f"移动文件失败: {e}")
            logger.info(f"导出 {draft_name} 至 {output_path} 完成")
            return True
        except Exception as e:
            logger.error(f"导出失败: {e}", exc_info=True)
            # 重启剪映
            JianyingStarter.restart_jianying()
        return False

    def export_draft_in_thread(
            self, draft_name: str, output_path: Optional[str] = None, timeout: float = 1200
    ) -> bool:
        """在线程中导出指定的剪映草稿"""
        try:
            with uia.UIAutomationInitializerInThread(debug=True):
                return self.export_draft(
                    draft_name=draft_name, output_path=output_path, timeout=timeout
                )
        except Exception as e:
            logger.error(f"在 export_draft_in_thread 中捕获到异常: {e}", exc_info=True)
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
                Compare=ControlFinder.desc_matcher(
                    f"HomePageDraftTitle:{draft_name}", exact=True
                ),
            )
            return draft_name_text.Exists(0)

        if not ControlFinder.wait_for_control(find_draft, timeout=3.0):
            return False

        draft_name_text = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher(
                f"HomePageDraftTitle:{draft_name}", exact=True
            ),
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
                Compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn"),
            )
            # 检查控件是否存在且可见
            if not export_btn.Exists(0.5):  # 给0.5秒时间查找控件
                return None
            # 使用 IsVisible() 方法检查可见性（如果库支持）
            if hasattr(export_btn, 'IsVisible') and not export_btn.IsVisible():
                return None
            # 使用 BoundingRectangle 检查控件是否有有效区域
            rect = export_btn.BoundingRectangle
            if rect.width() <= 0 or rect.height() <= 0:
                return None
            # 检查控件是否可点击
            if hasattr(export_btn, 'IsEnabled') and not export_btn.IsEnabled:
                return None
            return export_btn

        if not ControlFinder.wait_for_control(find_export_btn, timeout=8.0):
            logger.error(f"[find_export_btn] 未找到【导出】按钮")
            return False

        export_btn = self.app.TextControl(
            searchDepth=2,
            Compare=ControlFinder.desc_matcher("MainWindowTitleBarExportBtn"),
        )
        logger.info(f"[find_export_btn] 找到【导出】按钮 export_btn={export_btn}")

        click_res = ControlFinder.retry_click_enhanced(export_btn, delay=0.5)
        if not click_res:
            logger.error(f"[click_export_btn] 点击【导出】按钮失败")
            return click_res
        logger.info(f"[click_export_btn] 点击【导出】按钮成功")
        return True

    def _wait_for_export_page_ready(self) -> bool:
        """等待导出页面加载完成，通过检查导出路径控件是否存在来判断"""
        logger.info("正在等待导出页面加载完成...")

        def find_export_path_control():
            export_path_sib = self.app.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher("ExportPath")
            )
            return export_path_sib.Exists(0)

        if ControlFinder.wait_for_control(find_export_path_control, timeout=3.0):
            logger.info("导出页面已加载，【导出路径】控件已找到")
            return True
        else:
            logger.error("导出页面未能在指定时间内加载或【导出路径】控件未找到")
            return False

    def _get_export_path(self) -> Optional[str]:
        """获取导出路径"""
        if not self.get_window():
            return None

        def find_export_path():
            export_path_sib = self.app.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher("ExportPath")
            )
            return export_path_sib.Exists(0)

        if not ControlFinder.wait_for_control(find_export_path, timeout=3.0):
            return None

        try:
            export_path_sib = self.app.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher("ExportPath")
            )
            export_path_text = export_path_sib.GetSiblingControl(lambda ctrl: True)
            if export_path_text:
                return export_path_text.GetPropertyValue(30159)
        except Exception as e:
            logger.error(f"获取导出路径失败: {e}", exc_info=True)

        return None

    def _set_export_settings(
            self,
            resolution: Optional[Export_resolution],
            framerate: Optional[Export_framerate],
    ) -> None:
        """设置导出参数"""

        def find_setting_group():
            setting_group = self.app.GroupControl(
                searchDepth=1,
                Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"),
            )
            return setting_group.Exists(0)

        if not ControlFinder.wait_for_control(find_setting_group, timeout=2.0):
            logger.error("警告: 未找到设置组，跳过参数设置")
            return

        setting_group = self.app.GroupControl(
            searchDepth=1,
            Compare=ControlFinder.class_name_matcher("PanelSettingsGroup_QMLTYPE"),
        )

        # 设置分辨率
        if resolution is not None:
            self._set_resolution(setting_group, resolution)

        # 设置帧率
        if framerate is not None:
            self._set_framerate(setting_group, framerate)

    def _set_resolution(
            self, setting_group: uia.Control, resolution: Export_resolution
    ) -> None:
        """设置分辨率"""
        try:
            resolution_btn = setting_group.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportSharpnessInput"),
            )

            if not resolution_btn.Exists(1.0):
                logger.error("警告: 未找到分辨率设置按钮")
                return

            if not ControlFinder.retry_click(resolution_btn, delay=0.3):
                logger.error("警告: 无法点击分辨率设置按钮")
                return

            resolution_item = self.app.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher(resolution.value)
            )

            if resolution_item.Exists(1.0):
                ControlFinder.retry_click(resolution_item, delay=0.3)
            else:
                logger.error(f"警告: 未找到{resolution.value}分辨率选项")
        except Exception as e:
            logger.error(f"设置分辨率失败: {e}", exc_info=True)

    def _set_framerate(
            self, setting_group: uia.Control, framerate: Export_framerate
    ) -> None:
        """设置帧率"""
        try:
            framerate_btn = setting_group.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher("FrameRateInput")
            )

            if not framerate_btn.Exists(1.0):
                logger.error("警告: 未找到帧率设置按钮")
                return

            if not ControlFinder.retry_click(framerate_btn, delay=0.3):
                logger.error("警告: 无法点击帧率设置按钮")
                return

            framerate_item = self.app.TextControl(
                searchDepth=2, Compare=ControlFinder.desc_matcher(framerate.value)
            )

            if framerate_item.Exists(1.0):
                ControlFinder.retry_click(framerate_item, delay=0.3)
            else:
                logger.error(f"警告: 未找到{framerate.value}帧率选项")
        except Exception as e:
            logger.error(f"设置帧率失败: {e}", exc_info=True)

    def _start_export(self) -> bool:
        """开始导出"""

        def find_export_btn():
            export_btn = self.app.TextControl(
                searchDepth=2,
                Compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True),
            )
            return export_btn.Exists(0)

        if not ControlFinder.wait_for_control(find_export_btn, timeout=2.0):
            return False

        export_btn = self.app.TextControl(
            searchDepth=2, Compare=ControlFinder.desc_matcher("ExportOkBtn", exact=True)
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
                Compare=ControlFinder.desc_matcher("ExportSucceedCloseBtn"),
            )

            if succeed_close_btn.Exists(0):
                # ControlFinder.retry_click(succeed_close_btn, delay=0.5)
                ControlFinder.send_esc_key()
                time.sleep(0.5)
                # 编辑状态
                self.app_status = "edit"
                return True

            time.sleep(check_interval)

        # 超时，回到编辑状态
        ControlFinder.send_esc_key()
        time.sleep(0.5)
        # 编辑状态
        self.app_status = "edit"
        return False

    def switch_to_home(self) -> bool:
        """切换到剪映主页"""
        if self.app_status == "home":
            return True

        if self.app_status != "edit":
            # logger.info("警告: 当前不在编辑模式，无法切换到主页")
            logger.warn("[切换到剪映主页] 当前不在编辑模式，尝试通过ESC回到编辑页")
            ControlFinder.send_esc_key()
            time.sleep(0.5)
            self.app_status = "edit"

        try:
            title_bar_buttons = []
            # 遍历直接子控件，查找所有 ClassName 为 "TitleBarButton" 的 GroupControl
            logger.info("[切换到剪映主页] 正在查找标题栏关闭按钮...")
            for control in self.app.GetChildren():
                if (
                        control.ClassName == "TitleBarButton"
                        and control.ControlType == uia.ControlType.GroupControl
                ):
                    title_bar_buttons.append(control)
                    # 打印找到的按钮信息，方便调试
                    # logger.info(f"[切换到剪映主页] 找到标题栏关闭按钮: Name={control.Name}, ClassName={control.ClassName}, Rect={control.BoundingRectangle}")

            if not title_bar_buttons:
                logger.error("[切换到剪映主页] 错误: 未找到任何标题栏按钮")
                return False

            # 找到最右侧的按钮（即通常的“X”关闭按钮）
            # 依据 BoundingRectangle.right 属性进行排序
            title_bar_buttons.sort(
                key=lambda c: c.BoundingRectangle.right, reverse=True
            )
            close_btn = title_bar_buttons[0]
            logger.info(
                f"[切换到剪映主页] 定位到最右侧按钮作为关闭按钮: Name={close_btn.Name}, ClassName={close_btn.ClassName}, Rect={close_btn.BoundingRectangle}"
            )

            # close_btn = self.app.GroupControl(
            #     searchDepth=1, ClassName="TitleBarButton", foundIndex=3
            # )
            if close_btn.Exists(3.0):
                ControlFinder.retry_click(close_btn, delay=0.5)
                return self.get_window()
        except Exception as e:
            logger.error(f"切换到主页失败: {e}", exc_info=True)

        return False

    def get_window(self) -> bool:
        """寻找剪映窗口并置顶"""
        try:
            # 如果已有窗口且存在，先取消置顶
            if hasattr(self, "app") and self.app.Exists(0):
                self.app.SetTopmost(False)

            # 查找剪映窗口
            self.app = uia.WindowControl(
                searchDepth=1, Compare=self.__jianying_window_cmp
            )
            if not self.app.Exists(2.0):  # 增加等待时间
                return False

            # 检查导出窗口
            export_window = self.app.WindowControl(searchDepth=1, Name="导出")
            if export_window.Exists(0):
                self.app = export_window
                self.app_status = "pre_export"

            # 激活并置顶窗口
            self.app.SetActive()
            self.app.SwitchToThisWindow()
            logger.info(f"获取窗口成功，窗口当前状态：{self.app_status}")
            return True
        except Exception as e:
            logger.info(f"获取窗口失败: {e}")
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
            logger.error(f"窗口比较器异常: {control.Name}, err:{str(e)}", exc_info=True)

        return False


class JianyingStarter:
    def __init__(self):
        pass

    @staticmethod
    def get_jianying_processes() -> List[psutil.Process]:
        """获取所有剪映进程"""
        processes = []
        jy_exe_names = ['jianyingpro.exe', '剪映专业版']
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                if proc.info['name'].lower() in jy_exe_names:
                    processes.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return processes

    @staticmethod
    def kill_jianying_processes(timeout: int = 20) -> bool:
        """强制终止所有剪映进程"""
        processes = JianyingStarter.get_jianying_processes()
        if not processes:
            logging.info("未找到剪映进程，无需终止")
            return True
        logging.info(f"找到 {len(processes)} 个剪映进程，正在强制终止...")
        killed = 0
        # 先尝试优雅终止
        for proc in processes:
            try:
                proc.terminate()
                killed += 1
            except psutil.AccessDenied:
                logging.warning(f"无权限终止进程 {proc.pid}")
            except Exception as e:
                logging.warning(f"终止进程 {proc.pid} 失败: {e}")
                continue

        # 对未响应的进程进行强制终止
        force_killed = 0
        for proc in processes:
            try:
                if proc.is_running():
                    proc.kill()
                    force_killed += 1
            except psutil.AccessDenied:
                logging.warning(f"无权限强制终止进程 {proc.pid}")
            except psutil.NoSuchProcess:
                continue

        # 等待进程终止
        wait_time = 0
        while JianyingStarter.get_jianying_processes() and wait_time < timeout:
            time.sleep(1)
            wait_time += 1

        logging.info(f"成功终止 {killed} 个剪映进程，强制终止 {force_killed} 个进程")
        if JianyingStarter.get_jianying_processes():
            logging.warning("部分剪映进程未成功终止！")
            return False
        return True

    @staticmethod
    def start_jianying(timeout=30) -> bool:
        """启动剪映程序"""
        jianying_path = AppConfig.JY_EXE_PATH
        if not jianying_path:
            logging.error("未找到剪映可执行文件路径，无法启动")
            return False
        if not os.path.exists(jianying_path):
            logging.error(f"剪映可执行文件路径不存在: {jianying_path}")
            return False
        try:
            # 使用os.startfile启动程序，适用于Windows系统
            os.startfile(jianying_path)
            logging.info(f"正在启动剪映: {jianying_path}")
            for i in range(timeout):
                if JianyingStarter.get_jianying_processes():
                    logging.info("剪映启动成功")
                    return True
                time.sleep(1)
            logging.error("剪映启动超时")
            return False
        except Exception as e:
            logging.error(f"启动剪映失败: {e}")
            return False

    @staticmethod
    def restart_jianying(retry: int = 3) -> bool:
        """重启剪映（强制终止后启动）"""
        logging.info("开始重启剪映...")
        for i in range(retry):
            try:
                # 强制终止剪映进程
                if JianyingStarter.kill_jianying_processes():
                    # 等待进程完全终止
                    time.sleep(2)
                    # 启动剪映
                    if JianyingStarter.start_jianying():
                        logging.info("剪映重启成功")
                        return True
                    else:
                        logging.warning(f"剪映启动失败，重试 {i + 1}/{retry}")
                else:
                    logging.warning(f"剪映终止失败，重试 {i + 1}/{retry}")
                # 重试间隔
                time.sleep(3)
            except Exception as e:
                logging.error(f"重启剪映时发生异常，重试 {i + 1}/{retry}: {e}")
        logging.error(f"达到最大重试次数，剪映重启失败")
        return False


if __name__ == "__main__":
    JianyingStarter.restart_jianying()
