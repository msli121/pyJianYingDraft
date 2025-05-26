"""
@File: house_video_clip_service.py
@Description: 房源视频脚本解析

@Author: lms
@Date: 2025/2/24 19:30
"""
import glob
import json
import logging
import os
import random
import time

import pyJianYingDraft as draft
from app.entity.jy_task import JyTaskOutputInfo
from app.enum.biz import BizPlatformTaskStatusEnum
from app.utils.qywx_utils import send_qywx_message
from app_config import AppConfig, BASE_DIR
from pyJianYingDraft import trange, Clip_settings
from app.utils.common_utils import get_current_datetime_str_, download_by_url_to_local
from app.utils.oss_utils import init_oss, upload_local_file_to_oss, \
    generate_get_url, process_url
from pyJianYingDraft.jianying_exporter import JianyingExporter

logger = logging.getLogger(__name__)

LOCAL_HOUSE_MATERIAL_DATA_DIR = os.path.join(BASE_DIR, 'data')
LOCAL_HOUSE_MATERIAL_BGM_DIR = os.path.join(BASE_DIR, 'data', 'bgm')
OSS_VIDEO_MAKING_PATH_PREFIX = 'video-making/data'  # OSS的视频剪辑数据存放前缀
OSS_VIDEO_MAKING_PUBLIC_PATH_PREFIX = 'video-making/public'  # OSS的视频剪辑公共素材存放前缀
OSS_VIDEO_MAKING_BGM_PATH_PREFIX = 'video-making/bgm'  # OSS的视频剪辑背景音乐存放前缀

BGM_VOLUME_MAP = {
    'PederB.Helland-ANewDay.mp3': 0.5,
    'Pianoboy高至豪_The_truth_that_you_leave.mp3': 0.3,
    '北野夏海-AThousandYears钢琴.mp3': 0.6,
    '残影_-_知我（钢琴版）.mp3': 0.4,
    '赵海洋_-_夜空的寂静_(夜色钢琴曲).mp3': 0.5,
}


# 下载视频脚本和素材
def download_video_script_and_material(task_id, house_no, video_script_url):
    if house_no is None or len(house_no) == 0:
        raise Exception("house_no不能为空")
    if not task_id:
        raise Exception("task_id不能为空")
    if video_script_url is None or len(video_script_url) == 0:
        raise Exception("video_script_url 不能为空")
    if not video_script_url.lower().startswith('http'):
        raise Exception(f"视频脚本文件地址不存在")

    bgm_data_dir = os.path.join(LOCAL_HOUSE_MATERIAL_BGM_DIR)
    data_dir = os.path.join(LOCAL_HOUSE_MATERIAL_DATA_DIR, house_no, str(task_id))
    os.makedirs(data_dir, exist_ok=True)
    os.makedirs(bgm_data_dir, exist_ok=True)

    # 从OSS下载脚本文件
    script_local_path = os.path.join(data_dir, 'video_script.json')
    if download_by_url_to_local(video_script_url, script_local_path):
        logging.info(f"视频脚本文件已下载到本地：{script_local_path}")
    else:
        logging.error(f"视频脚本文件下载失败：{video_script_url}")
        raise Exception(f"视频脚本文件下载失败：{video_script_url}")
    # 读取文件内容
    with open(script_local_path, 'r', encoding='utf-8') as f:
        video_script_data = json.load(f)
    # 下载背景音乐
    bgm_url = video_script_data.get('bgm_url')
    if bgm_url:
        basename = os.path.basename(process_url(bgm_url))
        music_local_path = os.path.join(LOCAL_HOUSE_MATERIAL_DATA_DIR, basename)
        if not os.path.exists(music_local_path):
            download_by_url_to_local(bgm_url, music_local_path)
        logging.info(f"背景音乐文件已下载到本地：{music_local_path}")
        video_script_data['bgm_local_path'] = music_local_path
    clips = video_script_data.get('clips', [])
    for clip in clips:
        clip_video_oss_path = clip.get('clip_video_oss_path')
        if clip_video_oss_path:
            filename = os.path.basename(process_url(clip_video_oss_path))
            clip_video_local_path = os.path.join(data_dir, filename)
            if not os.path.exists(clip_video_local_path):
                download_by_url_to_local(clip_video_oss_path, clip_video_local_path)
                logging.info(f"视频文件已下载到本地：{clip_video_local_path}")
            else:
                logging.info(f"视频文件已存在：{clip_video_local_path}")
            clip['clip_video_local_path'] = clip_video_local_path
        srt_oss_path = clip.get('srt_oss_path')
        if srt_oss_path:
            filename = os.path.basename(process_url(srt_oss_path))
            srt_local_path = os.path.join(data_dir, filename)
            if not os.path.exists(srt_local_path):
                download_by_url_to_local(srt_oss_path, srt_local_path)
                logging.info(f"SRT文件已下载到本地：{srt_local_path}")
            else:
                logging.info(f"SRT文件已存在：{srt_local_path}")
            clip['srt_local_path'] = srt_local_path
        wav_oss_path = clip.get('wav_oss_path')
        if wav_oss_path:
            filename = os.path.basename(process_url(wav_oss_path))
            wav_local_path = os.path.join(data_dir, filename)
            if not os.path.exists(wav_local_path):
                download_by_url_to_local(wav_oss_path, wav_local_path)
                logging.info(f"WAV文件已下载到本地：{wav_local_path}")
            else:
                logging.info(f"WAV文件已存在：{wav_local_path}")
            clip['wav_local_path'] = wav_local_path
    video_script_data['clips'] = clips
    with open(script_local_path, 'w', encoding='utf-8') as f:
        json.dump(video_script_data, f, ensure_ascii=False, indent=4)
    logging.info(f"视频脚本文件处理完成：{script_local_path}")
    return script_local_path


# 剪映自动剪辑
def jy_auto_cut(video_script_local_path, jy_draft_dir):
    if not os.path.exists(video_script_local_path):
        raise Exception("视频脚本文件不存在")
    if not os.path.exists(jy_draft_dir):
        raise Exception("剪映草稿文件夹不存在")
    with open(video_script_local_path, 'r', encoding='utf-8') as f:
        video_script_data = json.load(f)

    #################### 调整配置的核心区域 #############################
    # 字体
    font = draft.Font_type.抖音美好体
    # font = draft.Font_type.新青年体
    # 字体颜色 暖色调的橙黄色
    text_style = draft.Text_style(color=(0.9, 0.9, 0.8), size=14, align=1, bold=True)
    # 文案相对中间区域的偏移
    transform_y = -0.5
    ##################################################################

    # 创建剪映草稿
    script = draft.Script_file(1080, 1920)  # 1080x1920分辨率
    # 添加视频轨道
    video_track_name = 'video'
    script.add_track(track_type=draft.Track_type.video, track_name=video_track_name)
    # 添加音频轨道
    audio_track_name = 'audio'
    script.add_track(track_type=draft.Track_type.audio, track_name=audio_track_name)
    # 添加字幕轨道
    subtitle_track_name = 'subtitle'
    script.add_track(track_type=draft.Track_type.text, track_name=subtitle_track_name)
    # 读取素材片段
    clips = video_script_data.get('clips', [])
    time_offset = 0
    for index, clip in enumerate(clips):
        clip_duration = 0
        # 处理音频素材
        wav_local_path = clip.get('wav_local_path')
        if os.path.exists(wav_local_path):
            wav_material = draft.Audio_material(wav_local_path)
            # 草稿中添加音频素材
            script.add_material(wav_material)
            # 添加音频片段
            audio_segment = draft.Audio_segment(wav_material, trange(time_offset, wav_material.duration))
            # 增加一个1s的淡入
            if index == 0:
                audio_segment.add_fade("1s", "0s")
            elif index == len(clips) - 1:
                audio_segment.add_fade("0s", "1s")
            # 添加音频片段到音频轨道
            script.add_segment(audio_segment, track_name=audio_track_name)
            # 本次片段时间
            clip_duration = wav_material.duration
        # 处理视频素材
        clip_video_local_path = clip.get('clip_video_local_path')
        if os.path.exists(clip_video_local_path):
            video_material = draft.Video_material(clip_video_local_path)
            # 草稿中添加视频素材
            script.add_material(video_material)
            # 没有音频文件，视频时长等于本次片段时长
            if clip_duration == 0:
                clip_duration = video_material.duration
            # 添加视频片段
            video_segment = draft.Video_segment(video_material, trange(time_offset, clip_duration),
                                                source_timerange=trange(0, video_material.duration))
            # 添加视频片段到视频轨道
            script.add_segment(video_segment, track_name=video_track_name)
        # 处理字幕素材
        srt_local_path = clip.get('srt_local_path')
        if os.path.exists(srt_local_path):
            # 参考的文字样式
            style_reference = draft.Text_segment("", trange("0s", "10s"),
                                                 font=font,
                                                 style=text_style,
                                                 clip_settings=Clip_settings(transform_y=transform_y))
            style_reference.add_bubble("532597",
                                       "6797267554562740743")  # 添加文本气泡效果, 相应素材元数据的获取参见readme中"提取素材元数据"部分
            style_reference.add_effect("7212892034623950141")
            script.import_srt(srt_local_path,
                              track_name=subtitle_track_name,
                              time_offset=time_offset,
                              style_reference=style_reference,
                              )
        # 更新下一个片段的起始时间
        time_offset += clip_duration

    # 背景音乐轨道
    bgm_local_path = video_script_data.get('bgm_local_path')
    if not bgm_local_path:
        music_files = glob.glob(os.path.join(LOCAL_HOUSE_MATERIAL_BGM_DIR, '*.mp3'))
        # 从 music_files 中随机选择一个
        bgm_local_path = random.choice(music_files) if music_files else None
    if bgm_local_path and os.path.exists(bgm_local_path):
        # 添加背音乐音频轨道
        bgm_track_name = 'bgm'
        bgm_basename = os.path.basename(bgm_local_path)
        script.add_track(track_type=draft.Track_type.audio, track_name=bgm_track_name)
        bgm_material = draft.Audio_material(bgm_local_path)
        script.add_material(bgm_material)
        volume = BGM_VOLUME_MAP.get(bgm_basename, 0.6)
        logging.info(f'背景音乐: {bgm_local_path}, 音量：{volume}')
        # 添加背景音乐片段
        bgm_segment = draft.Audio_segment(bgm_material, trange("0s", script.duration),
                                          volume=volume)
        # 增加一个1s的淡入和淡出
        bgm_segment.add_fade("1s", "1s")
        # 添加背景音乐到音频轨道
        script.add_segment(bgm_segment, track_name=bgm_track_name)

    # 保存草稿
    script.dump(os.path.join(jy_draft_dir, 'draft_content.json'))


# 自动导出视频
def jy_auto_export_video(jy_draft_name, video_save_path):
    # 此前需要将剪映打开，并位于目录页
    start_time = time.time()
    exporter = JianyingExporter()
    export_success = exporter.export_draft_in_thread(jy_draft_name, video_save_path)
    logging.info(f"导出完成 耗时：{time.time() - start_time:.2f}秒")
    return export_success


# 剪映自动一步到位，下载素材+剪辑+导出+上传OSS
def jy_auto_cut_and_export_one_step(task_id, house_no, video_script_url):
    jy_draft_name = "自动化剪辑"
    jy_draft_dir = os.path.join("D:\\Documents\\JianYingData\\JianyingPro Drafts", jy_draft_name)
    # 下载视频脚本和素材
    logging.info("[下载视频脚本和素材] 开始进行...")
    script_local_path = download_video_script_and_material(task_id, house_no, video_script_url)
    logging.info("[下载视频脚本和素材] 完成")
    # 剪映自动剪辑
    logging.info("[剪映自动化剪辑] 开始进行...")
    jy_auto_cut(script_local_path, jy_draft_dir)
    logging.info("[剪映自动化剪辑] 完成")
    # 剪映自动导出视频
    logging.info("[剪映自动化导出视频] 开始进行...")
    filename = f"{house_no}_{task_id}_{get_current_datetime_str_()}.mp4"
    video_save_path = os.path.join(LOCAL_HOUSE_MATERIAL_DATA_DIR, "ai_clip_finish", filename)
    os.makedirs(os.path.dirname(video_save_path), exist_ok=True)
    if not jy_auto_export_video(jy_draft_name, video_save_path):
        raise Exception("自动导出视频失败")
    logging.info(f"[自动导出视频] 完成 视频地址={video_save_path}")
    # 视频上传OSS
    oss_path = video_save_path.replace(LOCAL_HOUSE_MATERIAL_DATA_DIR, OSS_VIDEO_MAKING_PUBLIC_PATH_PREFIX)
    # 替换oss_path中 \ 为 /
    oss_path = oss_path.replace("\\", "/")
    logging.info(f"[视频上传OSS] {video_save_path} -> {oss_path}")
    if not upload_local_file_to_oss(local_file_path=video_save_path, oss_file_path=oss_path):
        raise Exception("成品视频上传OSS失败")
    logging.info("[视频上传OSS] 完成")
    # 拼接OSS地址
    url = generate_get_url(oss_path)
    if url:
        url = url.split("?")[0]
    logging.info(f"url={url}")
    return url


def handle_auto_clip_house_video(data: dict) -> JyTaskOutputInfo:
    task_id = data.get('task_id')
    house_no = data.get("house_no")
    video_script_url = data.get("video_script_url")
    notify_url = data.get("notify_url")
    staff_id = data.get("staff_id")
    nickname = data.get("nickname")
    output_info = JyTaskOutputInfo()
    try:
        if not house_no:
            raise ValueError("缺少房源编号")
        if not video_script_url:
            raise ValueError("缺少视频脚本地址")
        url = jy_auto_cut_and_export_one_step(task_id=task_id, house_no=house_no, video_script_url=video_script_url)
        if notify_url:
            message = (f"AI智能剪辑成功！\n"
                       f"任务ID:{task_id}\n"
                       f"房源编号: {house_no}\n"
                       f"员工号:{staff_id}\n"
                       f"昵称:{nickname}\n"
                       f"视频URL: {url}")
            send_qywx_message(message, url=notify_url)
        output_info.success = True
        output_info.task_status = BizPlatformTaskStatusEnum.DoneSuccess.value
        output_info.task_message = BizPlatformTaskStatusEnum.DoneSuccess.desc
        output_info.text_content = url
        return output_info
    except Exception as e:
        logger.error("[房源视频自动剪辑] Error: %s", str(e), exc_info=True)
        if notify_url:
            message = (f"AI智能剪辑失败！\n"
                       f"任务ID:{task_id}\n"
                       f"房源编号: {house_no}\n"
                       f"员工号:{staff_id}\n"
                       f"昵称:{nickname}\n"
                       f"错误信息：{str(e)}\n")
            send_qywx_message(message, url=notify_url)
        output_info.success = False
        output_info.task_status = BizPlatformTaskStatusEnum.DoneFail.value
        output_info.task_message = str(e)
        return output_info


if __name__ == '__main__':
    # 初始化OSS配置
    config = AppConfig()
    init_oss(access_key_id=config.ACCESS_KEY_ID, access_key_secret=config.ACCESS_KEY_SECRET,
             endpoint=config.ENDPOINT, bucket_name=config.BUCKET_NAME)
    house_no = 'TWZ2025021301115'
    video_script_oss_path = "video-mix/demo/TWZ2025021301115/分镜素材/素材_2025-02-26_19-52-43/video_script.json"
    logging.info("[剪映自动化导出视频] 开始进行...")
    data_dir = os.path.join(BASE_DIR, "data")
    file_name = f"{house_no}_{get_current_datetime_str_()}.mp4"
    video_save_path = os.path.join(LOCAL_HOUSE_MATERIAL_DATA_DIR, "ai_clip_finish", file_name)
    os.makedirs(os.path.dirname(video_save_path), exist_ok=True)
    jy_draft_name = "自动化剪辑"
    jy_auto_export_video(jy_draft_name, video_save_path)
    logging.info(f"[剪映自动化导出视频] 完成 视频地址={video_save_path}")
