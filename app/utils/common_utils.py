import base64
import datetime
import hashlib
import io
import logging
import os
import random
import shutil
import string
import time
from pathlib import Path
import socket

import requests
from PIL import Image


def is_video_url(url_or_path):
    """
    判断给定的URL地址或者OSS路径是否为视频类型的地址。

    :param url_or_path: URL地址或者OSS路径字符串
    :return: 如果是视频类型的地址返回True，否则返回False
    """
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv']
    url_path = url_or_path.lower()  # 将路径转换为小写

    for ext in video_extensions:
        if ext in url_path:
            return True

    return False


def is_image_url(url_or_path):
    """
    判断给定的URL地址或者OSS路径是否为图片类型的地址。

    :param url_or_path: URL地址或者OSS路径字符串
    :return: 如果是图片类型的地址返回True，否则返回False
    """
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp']
    # 将路径转换为小写
    url_path = url_or_path.lower()
    for ext in image_extensions:
        if ext in url_path:
            return True
    return False


# 随机生成指定长度的字符串
def generate_random_string(length=6):
    # Define the possible characters: uppercase, lowercase letters and digits
    characters = string.ascii_letters + string.digits
    # Generate a random string
    random_string = ''.join(random.choices(characters, k=length))
    return random_string


# 获取当前日期字符串，格式为YYYYMMDD
def get_current_day_str():
    return datetime.datetime.now().strftime("%Y%m%d")


# 获取当前日期时间字符串，格式为YYYY-MM-DD HH:MM:SS
def get_current_datetime_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# 获取当前日期时间字符串，格式为YYYY-MM-DD HH_MM_SS
def get_current_datetime_str_():
    return datetime.datetime.now().strftime("%Y-%m-%d_%H_%M_%S")


# 随机生成指定长度的字符串，并添加日期前缀
def generate_random_string_with_day_prefix(length=6):
    # 当前日期对应的字符串
    current_date_str = get_current_day_str()
    return current_date_str + generate_random_string(length=length).upper()


# 校验指定文件地址对应文件是否存在，不存在则新建文件
def check_file_exist(file_path, need_new=False):
    if not Path(file_path).exists():
        if need_new:
            dir_name = os.path.dirname(file_path)
            if not os.path.exists(dir_name):
                os.makedirs(dir_name)
        return False
    return True


# 移除文件路径中的本地文件路径前缀
# def remove_local_file_path_prefix(file_path):
#     if file_path is None or file_path == '':
#         return ""
#     if file_path.startswith(str(BASE_DIR)):
#         return file_path[len(str(BASE_DIR)):]
#     return file_path


# 获取两个日期之间的天数间隔 日期格式是YYYY-MM-DD
def get_day_interval(start_date, end_date):
    # 将字符串日期转换为 datetime 对象
    start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    # 计算两个日期之间的间隔
    day_interval = (end_date_obj - start_date_obj).days

    return day_interval


# 获取两个日期之间的所有日期
def get_all_days(start_date, end_date):
    # 将字符串日期转换为 datetime 对象
    start_date_obj = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end_date_obj = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    # 计算两个日期之间的间隔
    day_interval = (end_date_obj - start_date_obj).days
    # 生成日期列表
    date_list = [(start_date_obj + datetime.timedelta(days=i)).strftime('%Y-%m-%d') for i in range(day_interval + 1)]
    return date_list


# 在抖音限制的发布时间范围里
def is_within_time_range(time_str):
    # 将输入的时间字符串转换为 datetime 对象
    given_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M')
    # 获取当前时间
    current_time = datetime.datetime.now()
    # 计算未来的2小时和14天的时间点
    future_3_hours = current_time + datetime.timedelta(hours=3)
    future_14_days_end = (current_time + datetime.timedelta(days=14)).replace(hour=23, minute=59, second=59)
    # 判断给定时间是否在未来2小时之后，并且不超过未来14天的23:59:59
    return future_3_hours <= given_time <= future_14_days_end


def timestamp_to_beijing_time(timestamp):
    # 创建一个UTC时间对象
    utc_time = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)

    # 北京时间相对于UTC时间提前8个小时
    beijing_time = utc_time + datetime.timedelta(hours=8)

    # 将时间格式化为字符串
    beijing_time_str = beijing_time.strftime('%Y-%m-%d %H:%M:%S')

    return beijing_time_str


# 删除指定文件夹下的文件和文件夹，保留最近days天的文件和文件夹
def delete_old_files_and_folders(directory="./log", days=5):
    print(f"Deleting files and folders in {directory} older than {days} days...")
    # 获取当前时间的时间戳
    current_time = time.time()
    # 判断指定的目录是否存在
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist.")
        return
    # 遍历指定目录中的所有文件和文件夹
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        # 获取文件或文件夹的创建时间
        creation_time = os.path.getctime(file_path)

        # 计算文件或文件夹创建时间与当前时间的差值（秒）
        time_difference = current_time - creation_time

        # 如果时间差值大于指定天数（转换为秒），则删除文件或文件夹
        if time_difference > days * 86400:  # 86400秒 = 1天
            if os.path.isdir(file_path):
                # 如果是文件夹，使用shutil.rmtree删除
                shutil.rmtree(file_path)
                print(f"Deleted folder: {file_path}")
            else:
                # 如果是文件，使用os.remove删除
                os.remove(file_path)
                print(f"Deleted file: {file_path}")


# 等比例压缩图片
def compress_image(image_path, max_size_in_mb=5):
    """
    压缩图片使其大小小于指定的MB数。
    :param image_path: 本地图片路径
    :param max_size_in_mb: 最大文件大小（以MB为单位）
    :return: 压缩后的图片字节流
    """
    max_size = max_size_in_mb * 1024 * 1024  # 转换为字节
    img = Image.open(image_path)

    # 初始化图片字节流
    img_byte_arr = io.BytesIO()

    # 逐步降低质量压缩图片
    quality = 95  # 初始质量
    while True:
        img_byte_arr.seek(0)
        img.save(img_byte_arr, format=img.format, quality=quality)

        size = img_byte_arr.tell()
        if size <= max_size or quality <= 10:
            break

        # 每次循环减小质量
        quality -= 5

    return img_byte_arr.getvalue()


# 随机生成4位数字验证码
def generate_verification_code():
    return random.randint(1000, 9999)


# 随机生成6位数字的租户ID
def generate_tenant_id():
    return random.randint(100000, 999999)


# 判断是否为11位的手机号
def is_valid_phone_number(phone_number):
    if len(phone_number) == 11 and phone_number.isdigit():
        return True
    return False


# 判断给定的时间字符串是否已过期
def is_expired(time_str):
    """
    判断给定的时间字符串是否已过期

    :param time_str: 时间字符串，格式为 '%Y-%m-%d %H:%M:%S'
    :return: 如果已过期返回 True，否则返回 False
    """
    # 将字符串转换为 datetime 对象
    end_time = datetime.datetime.strptime(time_str, '%Y-%m-%d %H:%M:%S')
    # 获取当前时间
    current_time = datetime.datetime.now()
    # 判断是否过期
    return end_time < current_time


# 去掉数字结尾的多余零
def remove_trailing_zeros(value):
    """
    去掉数字结尾的多余零
    :param value: 传入的浮动数字
    :return: 去掉多余零后的数字
    """
    # 将数字转换为字符串并去掉末尾多余的零
    return str(float(value)).rstrip('0').rstrip('.') if '.' in str(value) else str(value)


# 获取本月月初时间（即本月的第一天 00:00:00）
def get_month_begin_time(format=False):
    """
    获取本月月初时间（即本月的第一天 00:00:00）
    :return: 本月月初的 datetime 对象
    """
    today = datetime.datetime.today()
    # 获取当前月的第一天
    first_day_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if format:
        return first_day_of_month.strftime('%Y-%m-%d %H:%M:%S')
    return first_day_of_month


def generate_task_code():
    timestamp = int(time.time() * 1000)  # 当前时间戳（毫秒）
    random_number = random.randint(1000, 9999)  # 随机数
    task_code = f"{timestamp}-{random_number}"  # 示例输出: '1619175691823-2953'
    return task_code


# 生成任务码
def generate_task_code_with_prefix(prefix="TASK"):
    """
    Generate a unique task code using the current timestamp and a random hash for uniqueness.

    :param prefix: Optional prefix for the task code (e.g., TASK for tasks).
    :return: A unique task code string.
    """
    # Get the current date and time in YYYYMMDDHHMMSS format
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    # Generate a random string of 6 characters (letters and digits) for added uniqueness
    random_str = ''.join(random.choices(string.ascii_uppercase, k=6))
    # Combine timestamp and random string
    task_code = f"{prefix}{timestamp}{random_str}"
    return task_code


# 获取本月月末时间（即本月的最后一天 23:59:59）
def get_month_end_time(format=False):
    """
    获取本月月末时间（即本月的最后一天 23:59:59）
    :return: 本月月末的 datetime 对象
    """
    today = datetime.datetime.today()
    # 获取下个月的第一天
    if today.month == 12:
        first_day_of_next_month = today.replace(year=today.year + 1, month=1, day=1)
    else:
        first_day_of_next_month = today.replace(month=today.month + 1, day=1)

    # 本月最后一天是下个月的第一天的前一天
    last_day_of_month = first_day_of_next_month - datetime.timedelta(days=1)
    # 设置为 23:59:59
    end_of_month = last_day_of_month.replace(hour=23, minute=59, second=59, microsecond=999999)
    if format:
        return end_of_month.strftime('%Y-%m-%d %H:%M:%S')
    return end_of_month


#  base 64 编码格式
def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


# 获取最后一层的文件名和后缀名
# 例如：/path/to/your/file/example.txt
# 文件名: example
# 后缀名: .txt
def get_file_name_and_extension(file_path: str):
    # 获取最后一层的文件名
    file_name = os.path.basename(file_path)
    # 分离文件名和后缀
    name, extension = os.path.splitext(file_name)
    return name, extension


# 是否为中文字符
def is_chinese_string(char):
    return '\u4e00' <= char <= '\u9fff'


# 据文本内容判断是否需要使用图像增强
def check_image_can_refiner_by_texts(texts):
    # 户型图关键字
    house_plan_image_keywords = ["阳台", "卫生间", "客厅", "卧室", "厨房"]
    # 判断文本中是否包含户型图关键字
    for keyword in house_plan_image_keywords:
        if any(keyword in text for text in texts):
            return False
    detect_cn_text_str = 0
    for text in texts:
        for char in text:
            if is_chinese_string(char):
                detect_cn_text_str += 1
                if detect_cn_text_str > 6:
                    return False
    return True


def get_local_ip():
    try:
        # 创建一个 UDP 套接字（无需实际连接）
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # 连接到一个公共 DNS 服务器（不会发送数据）
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception as e:
        return "127.0.0.1"  # 失败时返回本地回环地址


def download_by_url_to_local(url, save_path):
    """下载地址内容到本地指定位置"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        response.raise_for_status()

        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"图片下载失败: {str(e)}")
        return False


def md5_str(text: str):
    return hashlib.md5(text.encode(encoding='UTF-8')).hexdigest()


if __name__ == '__main__':
    print(get_all_days('2023-01-01', '2023-01-01'))
    print(timestamp_to_beijing_time(1723813500))

    print("本地ip地址:", get_local_ip())
