"""
@File: auto_cut.py
@Description: 视频脚本解析

@Author: lms
@Date: 2025/2/24 19:30
"""
import json
import logging
import os

import app_config
import pyJianYingDraft as draft
from pyJianYingDraft import trange, Clip_settings
from utils.common_utils import get_current_datetime_str_
from utils.oss_utils import check_file_exists_in_oss, download_file_from_oss, init_oss, upload_local_file_to_oss, \
    generate_get_url

BGM_VOLUME_MAP = {
    'PederB.Helland-ANewDay.mp3': 0.5,
    'Pianoboy高至豪_The_truth_that_you_leave.mp3': 0.4,
    '北野夏海-AThousandYears钢琴.mp3': 0.6,
    '残影_-_知我（钢琴版）.mp3': 0.4,
    '赵海洋_-_夜空的寂静_(夜色钢琴曲).mp3': 0.5,
}


# 下载视频脚本和素材
def download_video_script_and_material(house_no, video_script_oss_path):
    if house_no is None or len(house_no) == 0:
        raise Exception("house_no不能为空")
    if not check_file_exists_in_oss(video_script_oss_path):
        raise Exception("OSS上视频脚本文件不存在")
    if not house_no in video_script_oss_path:
        raise Exception(f"视频脚本文件格式不正确 {video_script_oss_path}")
    # 获取当前项目路径
    data_dir = os.path.join(app_config.BASE_DIR, "data")
    os.makedirs(data_dir, exist_ok=True)
    # 查找房源编号在video_script_oss_path中位置
    index = video_script_oss_path.index(house_no)
    script_local_path = os.path.abspath(os.path.join(data_dir, video_script_oss_path[index:]))
    os.makedirs(os.path.dirname(script_local_path), exist_ok=True)
    # 从OSS下载脚本文件
    if not os.path.exists(script_local_path):
        download_file_from_oss(oss_file_path=video_script_oss_path, local_file_path=script_local_path)
    logging.info(f"视频脚本文件已下载到本地：{script_local_path}")
    # 读取文件内容
    with open(script_local_path, 'r', encoding='utf-8') as f:
        video_script_data = json.load(f)
    # 下载背景音乐
    music_oss_path = video_script_data.get('bgm_oss_path')
    if music_oss_path and check_file_exists_in_oss(music_oss_path):
        basename = os.path.basename(music_oss_path)
        music_local_path = os.path.abspath(os.path.join(data_dir, 'bgm', basename))
        os.makedirs(os.path.dirname(music_local_path), exist_ok=True)
        if not os.path.exists(music_local_path):
            download_file_from_oss(oss_file_path=music_oss_path, local_file_path=music_local_path)
        logging.info(f"背景音乐文件已下载到本地：{music_local_path}")
        video_script_data['bgm_local_path'] = music_local_path
    clips = video_script_data.get('clips', [])
    for clip in clips:
        clip_video_oss_path = clip.get('clip_video_oss_path')
        if clip_video_oss_path and check_file_exists_in_oss(clip_video_oss_path):
            index = video_script_oss_path.index(house_no)
            clip_video_local_path = os.path.abspath(os.path.join(data_dir, clip_video_oss_path[index:]))
            if not os.path.exists(clip_video_local_path):
                download_file_from_oss(oss_file_path=clip_video_oss_path, local_file_path=clip_video_local_path)
                logging.info(f"视频文件已下载到本地：{clip_video_local_path}")
            else:
                logging.info(f"视频文件已存在：{clip_video_local_path}")
            clip['clip_video_local_path'] = clip_video_local_path
        srt_oss_path = clip.get('srt_oss_path')
        if srt_oss_path and check_file_exists_in_oss(srt_oss_path):
            index = video_script_oss_path.index(house_no)
            srt_local_path = os.path.abspath(os.path.join(data_dir, srt_oss_path[index:]))
            if not os.path.exists(srt_local_path):
                download_file_from_oss(oss_file_path=srt_oss_path, local_file_path=srt_local_path)
                logging.info(f"SRT文件已下载到本地：{srt_local_path}")
            else:
                logging.info(f"SRT文件已存在：{srt_local_path}")
            clip['srt_local_path'] = srt_local_path
        wav_oss_path = clip.get('wav_oss_path')
        if wav_oss_path and check_file_exists_in_oss(wav_oss_path):
            index = video_script_oss_path.index(house_no)
            wav_local_path = os.path.abspath(os.path.join(data_dir, wav_oss_path[index:]))
            if not os.path.exists(wav_local_path):
                download_file_from_oss(oss_file_path=wav_oss_path, local_file_path=wav_local_path)
                logging.info(f"WAV文件已下载到本地：{wav_local_path}")
            else:
                logging.info(f"WAV文件已存在：{wav_local_path}")
            clip['wav_local_path'] = wav_local_path
    video_script_data['clips'] = clips
    with open(script_local_path, 'w', encoding='utf-8') as f:
        json.dump(video_script_data, f, ensure_ascii=False, indent=4)
    logging.info(f"视频脚本文件已更新：{script_local_path}")
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
            script.import_srt(srt_local_path, track_name=subtitle_track_name, time_offset=time_offset,
                              text_style=text_style, clip_settings=Clip_settings(transform_y=transform_y),
                              font=font)
        # 更新下一个片段的起始时间
        time_offset += clip_duration

    # 背景音乐轨道
    bgm_local_path = video_script_data.get('bgm_local_path')
    if bgm_local_path and os.path.exists(bgm_local_path):
        # 添加背音乐音频轨道
        bgm_track_name = 'bgm'
        bgm_basename = os.path.basename(bgm_local_path)
        script.add_track(track_type=draft.Track_type.audio, track_name=bgm_track_name)
        bgm_material = draft.Audio_material(bgm_local_path)
        script.add_material(bgm_material)
        # 添加背景音乐片段
        bgm_segment = draft.Audio_segment(bgm_material, trange("0s", script.duration),
                                          volume=BGM_VOLUME_MAP.get(bgm_basename, 0.6))
        # 增加一个1s的淡入和淡出
        bgm_segment.add_fade("1s", "1s")
        # 添加背景音乐到音频轨道
        script.add_segment(bgm_segment, track_name=bgm_track_name)

    # 保存草稿
    script.dump(os.path.join(jy_draft_dir, 'draft_content.json'))


# 自动导出视频
def jy_auto_export_video(jy_draft_name, video_save_path):
    # 此前需要将剪映打开，并位于目录页
    ctrl = draft.Jianying_controller()
    thread = ctrl.export_draft_in_thread(jy_draft_name, video_save_path)
    thread.join()


# 剪映自动一步到位，下载素材+剪辑+导出+上传OSS
def jy_auto_cut_and_export_one_step(house_no, video_script_oss_path):
    jy_draft_name = "自动化剪辑"
    jy_draft_dir = os.path.join("D:\\Documents\\JianYingData\\JianyingPro Drafts", jy_draft_name)
    # 下载视频脚本和素材
    logging.info("[下载视频脚本和素材] 开始进行...")
    script_local_path = download_video_script_and_material(house_no, video_script_oss_path)
    logging.info("[下载视频脚本和素材] 完成")
    # 剪映自动剪辑
    logging.info("[剪映自动化剪辑] 开始进行...")
    jy_auto_cut(script_local_path, jy_draft_dir)
    logging.info("[剪映自动化剪辑] 完成")
    # 剪映自动导出视频
    logging.info("[剪映自动化导出视频] 开始进行...")
    data_dir = os.path.join(app_config.BASE_DIR, "data")
    file_name = f"{house_no}_{get_current_datetime_str_()}.mp4"
    video_save_path = os.path.abspath(os.path.join(data_dir, "成品视频", file_name))
    os.makedirs(os.path.dirname(video_save_path), exist_ok=True)
    jy_auto_export_video(jy_draft_name, video_save_path)
    logging.info(f"[剪映自动化导出视频] 完成 视频地址={video_save_path}")
    # 视频上传OSS
    index = video_script_oss_path.index(house_no)
    oss_path = f"{video_script_oss_path[:index]}成品视频/{file_name}"
    logging.info(f"[视频上传OSS] {video_save_path} -> {oss_path}")
    upload_local_file_to_oss(local_file_path=video_save_path, oss_file_path=oss_path)
    logging.info("[视频上传OSS] 完成")
    # 拼接OSS地址
    oss_url = generate_get_url(oss_path)
    logging.info(f"oss_url={oss_url}")
    return oss_url, video_save_path


if __name__ == '__main__':
    # 初始化OSS配置
    config = app_config.AppConfig()
    init_oss(access_key_id=config.ACCESS_KEY_ID, access_key_secret=config.ACCESS_KEY_SECRET,
             endpoint=config.ENDPOINT, bucket_name=config.BUCKET_NAME)
    house_no = 'TWZ2025021301115'
    video_script_oss_path = "video-mix/demo/TWZ2025021301115/分镜素材/素材_2025-02-26_19-52-43/video_script.json"
    # # 剪映自动化剪辑+导出
    # oss_url, video_save_path = jy_auto_cut_and_export_one_step(house_no, video_script_oss_path)
    # logging.info(oss_url)
    # logging.info(video_save_path)

    logging.info("[剪映自动化导出视频] 开始进行...")
    data_dir = os.path.join(app_config.BASE_DIR, "data")
    file_name = f"{house_no}_{get_current_datetime_str_()}.mp4"
    video_save_path = os.path.abspath(os.path.join(data_dir, "成品视频", file_name))
    os.makedirs(os.path.dirname(video_save_path), exist_ok=True)
    jy_draft_name = "自动化剪辑"
    jy_auto_export_video(jy_draft_name, video_save_path)
    logging.info(f"[剪映自动化导出视频] 完成 视频地址={video_save_path}")
