"""
@File: run_demo.py
@Description: 视频脚本解析

@Author: lms
@Date: 2025/2/24 19:30
"""
import glob
import json
import logging
import os
import random

import pyJianYingDraft as draft
from pyJianYingDraft import trange, Clip_settings
from utils.oss_utils import check_file_exists_in_oss, download_file_from_oss


# 下载视频脚本和素材
def download_video_script_and_material(video_script_oss_path):
    if not check_file_exists_in_oss(video_script_oss_path):
        raise Exception("OSS上视频脚本文件不存在")
    if not 'TWS' in video_script_oss_path:
        raise Exception("视频脚本文件格式不正确")
    # 获取当前项目路径
    work_dir = os.path.join(os.getcwd())
    data_dir = os.path.join(work_dir, "data")
    os.makedirs(data_dir, exist_ok=True)
    # 查找TWS在video_script_oss_path中位置
    index = video_script_oss_path.index('TWS')
    script_local_path = os.path.abspath(os.path.join(data_dir, video_script_oss_path[index:]))
    os.makedirs(os.path.dirname(script_local_path), exist_ok=True)
    # 从OSS下载脚本文件
    if not os.path.exists(script_local_path):
        download_file_from_oss(oss_file_path=video_script_oss_path, local_file_path=script_local_path)
    logging.info(f"视频脚本文件已下载到本地：{script_local_path}")
    # 读取文件内容
    with open(script_local_path, 'r', encoding='utf-8') as f:
        video_script_data = json.load(f)
    clips = video_script_data.get('clips', [])
    for clip in clips:
        clip_video_oss_path = clip.get('clip_video_oss_path')
        if clip_video_oss_path and check_file_exists_in_oss(clip_video_oss_path):
            index = video_script_oss_path.index('TWS')
            clip_video_local_path = os.path.abspath(os.path.join(data_dir, clip_video_oss_path[index:]))
            if not os.path.exists(clip_video_local_path):
                download_file_from_oss(oss_file_path=clip_video_oss_path, local_file_path=clip_video_local_path)
                logging.info(f"视频文件已下载到本地：{clip_video_local_path}")
            else:
                logging.info(f"视频文件已存在：{clip_video_local_path}")
            clip['clip_video_local_path'] = clip_video_local_path
        srt_oss_path = clip.get('srt_oss_path')
        if srt_oss_path and check_file_exists_in_oss(srt_oss_path):
            index = video_script_oss_path.index('TWS')
            srt_local_path = os.path.abspath(os.path.join(data_dir, srt_oss_path[index:]))
            if not os.path.exists(srt_local_path):
                download_file_from_oss(oss_file_path=srt_oss_path, local_file_path=srt_local_path)
                logging.info(f"SRT文件已下载到本地：{srt_local_path}")
            else:
                logging.info(f"SRT文件已存在：{srt_local_path}")
            clip['srt_local_path'] = srt_local_path
        wav_oss_path = clip.get('wav_oss_path')
        if wav_oss_path and check_file_exists_in_oss(wav_oss_path):
            index = video_script_oss_path.index('TWS')
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
    # 创建剪映草稿
    script = draft.Script_file(1080, 1920)  # 1080x1920分辨率
    # 字体
    font = draft.Font_type.抖音美好体
    # 字体颜色 暖色调的橙黄色
    text_style = draft.Text_style(color=(0.9, 0.6, 0.3), size=10, align=1, bold=True)
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
    second_offset = 0
    for clip in clips:
        clip_duration = clip.get("clip_duration")
        clip_video_local_path = clip.get('clip_video_local_path')
        if os.path.exists(clip_video_local_path):
            video_material = draft.Video_material(clip_video_local_path)
            # 草稿中添加视频素材
            script.add_material(video_material)
            # 添加视频片段
            video_segment = draft.Video_segment(video_material, trange(f"{second_offset}s", f"{clip_duration}s"))
            # 添加视频片段到视频轨道
            script.add_segment(video_segment, track_name=video_track_name)
        wav_local_path = clip.get('wav_local_path')
        if os.path.exists(wav_local_path):
            wav_material = draft.Audio_material(wav_local_path)
            # 草稿中添加音频素材
            script.add_material(wav_material)
            # 添加音频片段
            audio_segment = draft.Audio_segment(wav_material, trange(f"{second_offset}s", wav_material.duration))
            # 增加一个1s的淡入
            audio_segment.add_fade("1s", "0s")
            # 添加音频片段到音频轨道
            script.add_segment(audio_segment, track_name=audio_track_name)

        srt_local_path = clip.get('srt_local_path')
        if os.path.exists(srt_local_path):
            script.import_srt(srt_local_path, track_name=subtitle_track_name, time_offset=f"{second_offset}s",
                              text_style=text_style, clip_settings=Clip_settings(transform_y=-0.8))
        # 更新下一个片段的起始时间
        second_offset += clip_duration

    # 背景音乐轨道
    bgm_files = glob.glob(os.path.join(os.path.join(os.getcwd()), 'data', '背景音乐', '北野夏海-AThousandYears钢琴.mp3'))
    if len(bgm_files) > 0:
        # 添加背音乐音频轨道
        bgm_track_name = 'bgm'
        script.add_track(track_type=draft.Track_type.audio, track_name=bgm_track_name)
        # 随机选一首背景音乐
        bgm_file = random.choice(bgm_files)
        bgm_material = draft.Audio_material(bgm_file)
        # 草稿中添加音频素材
        script.add_material(bgm_material)
        # 添加背景音乐片段
        bgm_segment = draft.Audio_segment(bgm_material, trange("0s", script.duration), volume=0.3)
        # 增加一个1s的淡入和淡出
        bgm_segment.add_fade("1s", "1s")
        # 添加背景音乐到音频轨道
        script.add_segment(bgm_segment, track_name=bgm_track_name)

    # 保存草稿
    script.dump(os.path.join(jy_draft_dir, 'draft_content.json'))


if __name__ == '__main__':
    video_script_oss_path = "video-mix/demo/TWS2024102000070/分镜素材/素材_2025-02-24_21-45-18/video_script.json"
    # 下载视频脚本和素材
    logging.info("[下载视频脚本和素材] 开始进行...")
    script_local_path = download_video_script_and_material(video_script_oss_path)
    logging.info("[下载视频脚本和素材] 完成")
    jy_draft_dir = "D:\\Documents\\JianYingData\\Drafts\\JianyingPro Drafts\\自动化剪辑"
    # 剪映自动剪辑
    logging.info("[剪映自动化剪辑] 开始进行...")
    jy_auto_cut(script_local_path, jy_draft_dir)
    logging.info("[剪映自动化剪辑] 完成")
