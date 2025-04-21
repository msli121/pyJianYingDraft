"""
@File: house_video_clip_service.py
@Description: 房源视频脚本解析

@Author: lms
@Date: 2025/2/24 19:30
"""
import logging
import os

import pyJianYingDraft as draft
from app.entity.jy_task import GoodStoryClipReqInfo, JyTaskOutputInfo
from app.enum.biz import BizPlatformTrackTypeEnum, BizPlatformSegmentTypeEnum, BizPlatformTaskStatusEnum
from app.utils.common_utils import get_current_datetime_str_, download_by_url_to_local
from app.utils.oss_utils import upload_local_file_to_oss, \
    generate_get_url, process_url
from app_config import BASE_DIR
from pyJianYingDraft import trange, Clip_settings, Intro_type, Transition_type

logger = logging.getLogger(__name__)

LOCAL_GOOD_STORY_MATERIAL_DATA_DIR = os.path.join(BASE_DIR, 'app', 'video_making', 'data', 'good_story')
LOCAL_GOOD_STORY_MATERIAL_BGM_DIR = os.path.join(BASE_DIR, 'app', 'video_making', 'bgm')
OSS_VIDEO_MAKING_PATH_PREFIX = 'video-making/data/good_story'  # OSS数据存放前缀
OSS_VIDEO_MAKING_BGM_PATH_PREFIX = 'video-making/bgm'  # OSS的视频剪辑背景音乐存放前缀

# 好人好事草稿名：故事片段模版
GOOD_STORY_CLIP_DRAFT_NAME = '故事片段模版'
GOOD_STORY_CLIP_DRAFT_FILE = os.path.join("D:\\Documents\\JianYingData\\JianyingPro Drafts", GOOD_STORY_CLIP_DRAFT_NAME)

BGM_VOLUME_MAP = {
    'PederB.Helland-ANewDay.mp3': 0.5,
    'Pianoboy高至豪_The_truth_that_you_leave.mp3': 0.3,
    '北野夏海-AThousandYears钢琴.mp3': 0.6,
    '残影_-_知我（钢琴版）.mp3': 0.4,
    '赵海洋_-_夜空的寂静_(夜色钢琴曲).mp3': 0.5,
}


class GoodStoryClipService:

    @staticmethod
    def generate_good_story_clip_one_step(req_data: GoodStoryClipReqInfo):
        """
        一步到位生成好人好事视频片段
        """
        output_info = JyTaskOutputInfo()
        try:
            # 下载素材
            GoodStoryClipService.download_good_story_material(req_data)
            # 剪辑
            GoodStoryClipService.cut_good_story_clip(req_data)
            # 导出
            local_path = GoodStoryClipService.export_good_story_clip(req_data.story_id)
            # 上传
            oss_url = GoodStoryClipService.upload_to_oss(local_path)
            output_info.success = True
            output_info.task_status = BizPlatformTaskStatusEnum.DoneSuccess.value
            output_info.task_message = BizPlatformTaskStatusEnum.DoneSuccess.desc
            output_info.text_content = oss_url
            return output_info
        except Exception as e:
            logger.error(f"生成好人好事视频片段失败：{e}", exc_info=True)
            output_info.success = False
            output_info.task_status = BizPlatformTaskStatusEnum.DoneFail.value
            output_info.task_message = str(e)
            return output_info

    @staticmethod
    def download_good_story_material(req_data: GoodStoryClipReqInfo):
        """下载故事素材"""
        if req_data is None:
            raise Exception("素材数据不能为空")
        story_id = req_data.story_id
        story_name = req_data.story_name
        logger.info(f"[开始下载故事素材] 故事ID：{story_id}, 故事名称：{story_name}")
        for track in req_data.tracks:
            for segment in track.segments:
                if segment.url:
                    filename = segment.filename
                    if not filename:
                        filename = os.path.basename(process_url(segment.url))
                    local_file_path = os.path.join(LOCAL_GOOD_STORY_MATERIAL_DATA_DIR, str(story_id), filename)
                    if not os.path.exists(local_file_path):
                        os.makedirs(os.path.dirname(local_file_path), exist_ok=True)
                        if download_by_url_to_local(segment.url, local_file_path):
                            segment.local_file_path = local_file_path
                            logger.info(
                                f"[下载故事素材成功] 故事ID：{story_id}, 故事名称：{story_name}, 素材URL：{segment.url}")
                        else:
                            raise Exception(
                                f"[下载故事素材失败] 故事ID：{story_id}, 故事名称：{story_name}, 素材URL：{segment.url}")
                    else:
                        segment.local_file_path = local_file_path
                        logger.info(f"[故事素材已存在] 故事ID：{story_id}, 故事名称：{story_name}, 素材URL：{segment.url}")

    @staticmethod
    def cut_good_story_clip(req_data: GoodStoryClipReqInfo):
        """自动裁剪故事片段"""
        if req_data is None:
            raise Exception("素材数据不能为空")
        if not os.path.isdir(GOOD_STORY_CLIP_DRAFT_FILE):
            raise Exception(f"故事片段模版 文件不存在：{GOOD_STORY_CLIP_DRAFT_FILE}")
        if not req_data.tracks or len(req_data.tracks) == 0:
            raise Exception("轨道信息不能为空")
        story_id = req_data.story_id
        story_name = req_data.story_name
        logger.info(f"[开始自动裁剪故事片段] 故事ID：{story_id}, 故事名称：{story_name}")

        #################### 调整配置的核心区域 #############################
        # 字体
        font = draft.Font_type.抖音美好体
        # font = draft.Font_type.新青年体
        # 标题字体颜色 暖色调的橙黄色
        title_text_style = draft.Text_style(color=(0.9, 0.9, 0.8), size=20, align=1, bold=True)
        # 字幕字体配置
        subtitle_text_style = draft.Text_style(size=16, align=1, bold=True)
        # 文案相对中间区域的偏移
        transform_y = -0.5
        # 创建剪映草稿
        script = draft.Script_file(1080, 1920)  # 1080x1920分辨率
        ##################################################################

        # 解析参数
        for track in req_data.tracks:
            track_type = track.track_type
            track_name = track.track_name
            track_mute = track.track_mute or False
            # 添加轨道
            if track_type == BizPlatformTrackTypeEnum.VIDEO.value:
                # 添加视频轨道
                script.add_track(track_type=draft.Track_type.video, track_name=track_name, mute=track_mute)
            elif track_type == BizPlatformTrackTypeEnum.AUDIO.value:
                # 添加音频轨道
                script.add_track(track_type=draft.Track_type.audio, track_name=track_name, mute=track_mute)
            elif track_type == BizPlatformTrackTypeEnum.TEXT.value:
                # 添加文本轨道
                script.add_track(track_type=draft.Track_type.text, track_name=track_name)
            else:
                raise Exception(f"不支持的轨道类型：{track_type}")
            # 添加轨道素材
            for segment in track.segments:
                if not segment.type:
                    continue
                segment_type = segment.type
                if segment_type == BizPlatformSegmentTypeEnum.VIDEO.value or segment_type == BizPlatformSegmentTypeEnum.IMAGE.value:
                    if not segment.local_file_path or not os.path.exists(segment.local_file_path):
                        raise Exception(f"素材文件不存在：{segment.local_file_path}")
                    video_material = draft.Video_material(segment.local_file_path)
                    video_segment = draft.Video_segment(video_material, trange(segment.start_time_ms * 1000,
                                                                               segment.duration_ms * 1000))
                    # 添加一个入场动画
                    if segment.has_entry_animation:
                        video_segment.add_animation(Intro_type.斜切)
                    # 添加一个转场类型
                    if segment.has_transition:
                        video_segment.add_transition(Transition_type.风车)
                    # 添加到视频轨道
                    script.add_segment(video_segment, track_name)
                elif segment_type == BizPlatformSegmentTypeEnum.AUDIO.value:
                    if not segment.local_file_path or not os.path.exists(segment.local_file_path):
                        raise Exception(f"素材文件不存在：{segment.local_file_path}")
                    segment_volume = segment.volume or 0.6
                    audio_material = draft.Audio_material(segment.local_file_path)
                    duration_time = min(segment.duration_ms * 1000, audio_material.duration)
                    audio_segment = draft.Audio_segment(audio_material,
                                                        trange(segment.start_time_ms * 1000,
                                                               duration_time),
                                                        volume=segment_volume
                                                        )
                    # 增加一个1s的淡入和淡出
                    audio_segment.add_fade("1s", "1s")
                    # 添加到音频轨道
                    script.add_segment(audio_segment, track_name)
                elif segment_type == BizPlatformSegmentTypeEnum.TEXT.value:
                    if not segment.text:
                        raise Exception(f"素材文本不存在")
                    text_segment = draft.Text_segment(
                        segment.text, trange(segment.start_time_ms * 1000,
                                             segment.duration_ms * 1000),
                        font=font,
                        style=title_text_style,  # 字体颜色为黄色
                        clip_settings=draft.Clip_settings(transform_y=0.8)  # 位置在屏幕上方
                    )
                    text_segment.add_effect("7403943938391887138")
                    script.add_segment(text_segment, track_name)
                elif segment_type == BizPlatformSegmentTypeEnum.SUBTITLE.value:
                    if not segment.local_file_path or not os.path.exists(segment.local_file_path):
                        raise Exception(f"素材文件不存在：{segment.local_file_path}")
                    # 参考的文字样式
                    style_reference = draft.Text_segment("", trange("0s", "10s"),
                                                         font=font,
                                                         style=subtitle_text_style,
                                                         clip_settings=Clip_settings(transform_y=transform_y))
                    style_reference.add_bubble("532597",
                                               "6797267554562740743")  # 添加文本气泡效果, 相应素材元数据的获取参见readme中"提取素材元数据"部分
                    style_reference.add_effect("7212892034623950141")
                    script.import_srt(segment.local_file_path,
                                      track_name=track_name,
                                      time_offset=segment.start_time_ms * 1000,
                                      style_reference=style_reference,
                                      )
        # 保存草稿
        script.dump(os.path.join(GOOD_STORY_CLIP_DRAFT_FILE, 'draft_content.json'))

    @staticmethod
    def export_good_story_clip(story_id: int) -> str:
        """导出好人好事故事片段"""
        if story_id is None or story_id <= 0:
            raise Exception("故事ID不能为空")
        if not os.path.exists(GOOD_STORY_CLIP_DRAFT_FILE):
            raise Exception(f"故事片段模版文件不存在：{GOOD_STORY_CLIP_DRAFT_FILE}")
        if not os.path.exists(GOOD_STORY_CLIP_DRAFT_FILE):
            raise Exception(f"好人好事故事片段草稿文件不存在：{GOOD_STORY_CLIP_DRAFT_FILE}")
        video_save_path = os.path.join(LOCAL_GOOD_STORY_MATERIAL_DATA_DIR, "clips",
                                       f"{story_id}_{get_current_datetime_str_()}.mp4")
        os.makedirs(os.path.dirname(video_save_path), exist_ok=True)
        ctrl = draft.Jianying_controller()
        export_success = ctrl.export_draft_in_thread(GOOD_STORY_CLIP_DRAFT_NAME, video_save_path)
        if not export_success:
            raise Exception(f"导出好人好事故事片段失败：{video_save_path}")
        return video_save_path

    @staticmethod
    def upload_to_oss(local_path: str) -> str:
        """上传到OSS"""
        if not os.path.exists(local_path):
            raise Exception(f"文件不存在：{local_path}")
        # 视频上传OSS
        oss_path = local_path.replace(LOCAL_GOOD_STORY_MATERIAL_DATA_DIR, OSS_VIDEO_MAKING_PATH_PREFIX)
        # 替换oss_path中 \ 为 /
        oss_path = oss_path.replace("\\", "/")
        logging.info(f"[视频上传OSS] {local_path} -> {oss_path}")
        if not upload_local_file_to_oss(local_file_path=local_path, oss_file_path=oss_path):
            raise Exception("成品视频上传OSS失败")
        logging.info("[视频上传OSS] 完成")
        # 拼接OSS地址
        url = generate_get_url(oss_path)
        if url:
            url = url.split("?")[0]
        logging.info(f"url={url}")
        return url
