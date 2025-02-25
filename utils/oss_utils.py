import os
import re
import urllib
from enum import Enum
from urllib.parse import urlparse, parse_qs
import requests
from PIL import Image
import io
import oss2
import base64
import hmac
import json
import datetime
from hashlib import sha1

import logging
import app_config

from utils.common_utils import is_image_url, is_video_url, compress_image

# 使用标准库 logging 来获取日志记录器
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
)
logger = logging.getLogger(__name__)

# 全局变量
bucket = None
ACCESS_KEY_ID = None
ACCESS_KEY_SECRET = None


class OssOperationType(Enum):
    GET = 'GET'
    PUT = 'PUT'


def init_oss(access_key_id, access_key_secret, endpoint, bucket_name):
    # 初始化OSS配置
    global bucket, ACCESS_KEY_ID, ACCESS_KEY_SECRET
    ACCESS_KEY_ID = access_key_id
    ACCESS_KEY_SECRET = access_key_secret
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)


def upload_local_file_to_oss(local_file_path, oss_file_path, need_compress=False, max_size_in_mb=5):
    try:
        # 上传文件
        if need_compress and is_image_url(local_file_path):
            # 压缩图片
            compressed_image = compress_image(local_file_path, max_size_in_mb * 1024 * 1024)
            # 上传压缩后的图片到OSS
            bucket.put_object(oss_file_path, compressed_image)
        else:
            bucket.put_object_from_file(oss_file_path, local_file_path)
        # print(f"文件 {local_file_path} 成功上传到 OSS 路径 {oss_file_path}")
        return True, "success"
    except Exception as e:
        # 处理上传异常
        print(f"上传文件到OSS失败：{e}")
        return False, f"上传文件到OSS失败：{e}"


def upload_file_data_to_oss(file_data, oss_file_path, need_compress=False, max_size_in_mb=5):
    try:
        if need_compress:
            # 假设这里有一个临时文件路径，用于将文件数据保存为临时文件以便进行压缩
            temp_file_path = 'temp_file_for_compression'
            with open(temp_file_path, 'wb') as f:
                f.write(file_data)

            if is_image_url(oss_file_path):
                # 压缩图片
                compressed_image = compress_image(temp_file_path, max_size_in_mb * 1024 * 1024)
                # 上传压缩后的图片到 OSS
                bucket.put_object(oss_file_path, compressed_image)
            else:
                bucket.put_object(oss_file_path, file_data)
        else:
            bucket.put_object(oss_file_path, file_data)

        print(f"文件数据成功上传到 OSS 路径 {oss_file_path}")
        return True, "success"
    except Exception as e:
        # 处理上传异常
        print(f"上传文件数据到 OSS 失败：{e}")
        return False, f"上传文件数据到 OSS 失败：{e}"


# 上传指定网络地址的图片到 OSS
def upload_image_url_to_oss(image_url, oss_path):
    """
    上传指定网络地址的图片到 OSS

    :param image_url: 网络图片的 URL
    :param oss_path: OSS 上的目标路径
    :return: 上传结果的元组 (成功标志, 消息)
    """
    try:
        # 下载图片
        response = requests.get(image_url)
        response.raise_for_status()  # 确保请求成功
        # 上传文件
        bucket.put_object(oss_path, response.content)
        print(f"图片 {image_url} 成功上传到 OSS 路径 {oss_path}")
        return True, "success"
    except Exception as e:
        # 处理上传异常
        print(f"上传文件到 OSS 失败：{e}")
        return False, f"上传文件到 OSS 失败：{e}"


def download_file_from_oss(oss_file_path, local_file_path):
    """
    从OSS下载对象到本地文件
    Args:
        oss_file_path: OSS对象路径
        local_file_path: 本地文件路径
    Returns:
        Tuple: (成功标志, 消息)
    """
    try:
        # 创建本地文件夹（如果不存在）
        local_dir = os.path.dirname(local_file_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # 处理OSS文件路径
        oss_file_path = process_url(oss_file_path)

        # 下载文件
        bucket.get_object_to_file(oss_file_path, local_file_path)
        print(f"文件 {oss_file_path} 成功下载到本地路径 {local_file_path}")
        return True, "success"
    except Exception as e:
        # 处理下载异常
        print(f"从OSS下载文件失败：{e}")
        return False, f"从OSS下载文件失败：{e}"


def generate_get_url(oss_file_path, expiration=7200, scale=1.0):
    """
    生成可以在公网访问的HTTPS链接
    :param oss_file_path: OSS文件路径
    :param expiration: 链接有效期（秒），默认3600秒
    :param scale: 缩放比例，默认1， 2代表缩放一半
    :return: 生成的URL
    """
    try:
        if oss_file_path is None or oss_file_path == "":
            return None
        x_oss_process_value = None
        if oss_file_path.find("x-oss-process") != -1:
            # 解析URL
            parsed_url = urlparse(oss_file_path)
            # 提取查询参数
            query_params = parse_qs(parsed_url.query)
            # 获取x-oss-process对应的值
            x_oss_process_value = query_params.get('x-oss-process', [None])[0]
        # 处理OSS文件路径
        oss_file_path = process_url(oss_file_path)
        if is_url_encoded(oss_file_path):
            print(f"[generate_get_url] URL已编码：{oss_file_path}")
            oss_file_path = urllib.parse.unquote(oss_file_path)
            print(f"[generate_get_url] URL解码后：{oss_file_path}")
        # 从URL里解析出来是否包含x-oss-process参数
        if scale != 1.0 and is_image_url(oss_file_path):
            scale = int(scale * 100)
            params = {
                "x-oss-process": f"image/resize,p_{scale}"
            }
            # 生成签名URL
            url = bucket.sign_url('GET', oss_file_path, expiration, params=params, slash_safe=True)
        elif x_oss_process_value is not None:
            params = {
                "x-oss-process": x_oss_process_value
            }
            # 生成签名URL
            url = bucket.sign_url('GET', oss_file_path, expiration, params=params, slash_safe=True)
        else:
            # 生成签名URL
            url = bucket.sign_url('GET', oss_file_path, expiration, slash_safe=True)
        # 将URL中的编码斜杠替换回斜杠
        # url = url.replace('%2F', '/')
        # print(f"[generate_get_url] 生成的URL为：{url}")
        return url
    except Exception as e:
        # 处理生成URL异常
        print(f"生成公有链接失败：{e}")
        return None


def generate_get_url_scale_max_side(oss_file_path, max_side=None, expiration=3600):
    """
        生成可以在公网访问的HTTPS链接
        :param oss_file_path: OSS文件路径
        :param expiration: 链接有效期（秒），默认3600秒
        :param max_side: 缩放后最大的像素
        :return: 生成的URL
        """
    try:
        if oss_file_path is None or oss_file_path == "":
            return None
        # 处理OSS文件路径
        oss_file_path = process_url(oss_file_path)
        if is_url_encoded(oss_file_path):
            print(f"[generate_get_url_scale_max_side] URL已编码：{oss_file_path}")
            oss_file_path = urllib.parse.unquote(oss_file_path)
            print(f"[generate_get_url_scale_max_side] URL解码后：{oss_file_path}")
        if max_side is not None and is_image_url(oss_file_path):
            params = {
                "x-oss-process": f"image/resize,l_{max_side}"
            }
            # 生成签名URL
            url = bucket.sign_url('GET', oss_file_path, expiration, params=params, slash_safe=True)
        else:
            # 生成签名URL
            url = bucket.sign_url('GET', oss_file_path, expiration, slash_safe=True)
        return url
    except Exception as e:
        # 处理生成URL异常
        print(f"生成公有链接失败：{e}")
        return None


def generate_put_url(oss_file_path, expiration=3600):
    """
    生成可以用于上传的URL
    :param oss_file_path: OSS文件路径
    :param expiration: 链接有效期（秒），默认3600秒
    :return: 生成的URL

    Args:
        content_type:
    """
    try:
        if oss_file_path is None or oss_file_path == "":
            return False, "地址为空"
        # 处理OSS文件路径
        oss_file_path = process_url(oss_file_path)
        # 指定Header
        headers = dict()
        # 判断oss_file_path是否为视频的地址
        if is_video_url(oss_file_path):
            headers['Content-Type'] = 'video/*'
        elif is_image_url(oss_file_path):
            headers['Content-Type'] = 'image/*'
        # 生成签名URL
        url = bucket.sign_url('PUT', oss_file_path, expiration, slash_safe=True, headers=headers)
        return True, url
    except Exception as e:
        # 处理生成URL异常
        print(f"生成公有链接失败：{e}")
        return False, str(e)


def delete_file_from_oss(oss_file_path):
    """
    删除指定路径的文件
    Args:
        oss_file_path (str): OSS文件路径
    Returns:
        Tuple: (成功标志, 消息)
    """
    try:
        # 处理OSS文件路径
        oss_file_path = process_url(oss_file_path)

        # 删除文件
        bucket.delete_object(oss_file_path)
        print(f"文件 {oss_file_path} 已成功从 OSS 删除")
        return True, "文件删除成功"
    except Exception as e:
        # 处理删除异常
        print(f"删除 OSS 文件失败：{e}")
        return False, f"删除 OSS 文件失败：{e}"


def list_keys(oss_dir):
    """
    递归获取该路径下所有的文件。
    Args:
        oss_dir (str): OSS目录路径

    Returns:
        list: 包含所有对象的key
    """
    try:
        # 获取指定路径下的所有文件
        all_files = []
        for obj in oss2.ObjectIterator(bucket, prefix=oss_dir):
            if obj.is_prefix():
                continue
            all_files.append(obj.key)
        return all_files
    except Exception as e:
        print(f"检查路径或获取文件列表失败：{e}")
        return []


def list_first_level_file_keys(oss_dir):
    """
    获取指定文件夹下的一级文件或文件夹。
    Args:
        oss_dir (str): OSS目录路径，必须以 '/' 结尾以表示文件夹

    Returns:
        list: 包含一级文件或文件夹的key
    """
    try:
        # 获取指定路径下的一级文件或文件夹
        first_level_files = []
        for obj in oss2.ObjectIterator(bucket, prefix=oss_dir, delimiter='/'):
            key = obj.key
            if not obj.is_prefix() and not key.endswith('/'):
                first_level_files.append(obj.key)
        return first_level_files
    except Exception as e:
        print(f"检查路径或获取文件列表失败：{e}")
        return []


# 获取指定OSS目录下的文件列表，并生成对应的URL
def list_first_level_oss_url(oss_dir, expiration=7200):
    keys = list_first_level_file_keys(oss_dir)
    # 获取排序后的文件URL
    oss_urls = [generate_get_url(key, expiration) for key in keys]
    return oss_urls


def process_url(url):
    if not url:
        return ""

    # 去除域名前缀
    if url.startswith("http"):
        url = re.sub(r"https?://[^/]+/", "/", url)

    # 去除 ? 及其后面的部分
    query_string_index = url.find('?')
    if query_string_index != -1:
        url = url[:query_string_index]

    # 去掉开头的/
    if url.startswith("/"):
        url = url[1:]

    return url


# 从oss路径中解析出来文件名
def parse_filename(oss_path):
    """
    从oss路径中解析出来文件名
    Args:
        oss_path:
    Returns:
    """
    if oss_path is None or oss_path == "":
        return None
    # 去除 ? 及其后面的部分
    query_string_index = oss_path.find('?')
    if query_string_index != -1:
        oss_path = oss_path[:query_string_index]
    return oss_path.split('/')[-1]


# 获取指定前缀下的最近n个文件
def list_recent_files(prefix, max_keys=9):
    """
    获取指定前缀下的最近n个文件
    Args:
        prefix:
        max_keys:
    Returns:
    """
    # 列出文件并按上传时间排序
    files = []
    for obj in oss2.ObjectIterator(bucket, prefix=prefix):
        files.append({
            'key': obj.key,
            'last_modified': obj.last_modified
        })

    # 按最后修改时间降序排序
    files.sort(key=lambda x: x['last_modified'], reverse=True)

    # 取最近的max_files个文件
    recent_files = files[:max_keys]

    # 获取排序后的文件URL
    image_urls = [generate_get_url(item['key']) for item in recent_files]

    return image_urls


# 是否进行过URL编码
def is_url_encoded(url):
    """ 检查 URL 是否已经编码 """
    return url != urllib.parse.unquote(url)


# 生成上传所需的参数，包括policy和signature
def create_upload_params():
    """生成上传所需的参数，包括policy和signature"""
    global ACCESS_KEY_ID, ACCESS_KEY_SECRET
    expiration = (datetime.datetime.utcnow() + datetime.timedelta(hours=1)).isoformat() + 'Z'
    policy_text = {
        "expiration": expiration,
        "conditions": [
            ["content-length-range", 0, 10 * 1024 * 1024],  # 限制上传文件大小,10MB
        ]
    }
    policy = json.dumps(policy_text).encode('utf-8')
    policy = base64.b64encode(policy).decode('utf-8')

    # 生成HMAC-SHA1签名
    h = hmac.new(ACCESS_KEY_SECRET.encode('utf-8'), policy.encode('utf-8'), sha1)
    signature = base64.b64encode(h.digest()).decode('utf-8')
    return {
        'OSSAccessKeyId': ACCESS_KEY_ID,
        'policy': policy,
        'signature': signature,
    }


# 获取OSS图片信息
def get_image_info(oss_file_path, scale=1.0):
    """
    获取OSS图片信息
    :param oss_file_path: OSS文件路径
    :scale: 缩放比例，默认为1
    :return: 图片的宽度和高度 (width, height)，如果获取失败则返回 None
    """
    try:
        # 判断是否包含 'x-oss-process'
        if 'x-oss-process' in oss_file_path:
            return get_image_info_by_download(oss_file_path)
        else:
            return get_image_info_by_oss(oss_file_path, scale)
    except Exception as e:
        print(f"获取图片信息失败：{e}")
        return None


def get_image_info_by_oss(oss_file_path, scale=1.0):
    """
        获取OSS图片信息
        :param oss_file_path: OSS文件路径
        :scale: 缩放比例，默认为1
        :return: 图片的宽度和高度 (width, height)，如果获取失败则返回 None
        """
    try:
        logger.info(f"[get_image_info_by_oss] 正在获取图片信息: {oss_file_path}")
        oss_file_path = process_url(oss_file_path)
        # 构建获取图片信息的处理指令。
        process = 'image/info'
        # 使用get_object方法，并通过process参数传入处理指令。
        result = bucket.get_object(oss_file_path, process=process)
        image_info = result.read().decode('utf-8')
        image_info = json.loads(image_info)
        width = int(image_info["ImageWidth"]["value"])
        height = int(image_info["ImageHeight"]["value"])
        return {
            "width": int(width * scale),
            "height": int(height * scale),
        }
    except Exception as e:
        print(f"获取图片信息失败：{e}")
        return None


# 获取图片的宽度、高度信息
def get_image_info_by_download(image_url):
    """
    获取图片的宽度和高度

    :param image_url: 图片的URL地址
    :return: 包含宽度和高度的字典，或None（在出错时）
    """
    try:
        # 发送HTTP GET请求获取图片，启用流模式
        logger.info(f"[get_image_info_by_download] 正在获取图片信息: {image_url}")
        with requests.get(image_url, timeout=10, stream=True) as response:
            response.raise_for_status()
            # 使用Pillow打开图片并获取尺寸，避免下载整个文件
            with Image.open(io.BytesIO(response.content)) as img:
                width, height = img.size
        return {
            "width": width,
            "height": height
        }
    except requests.exceptions.Timeout:
        print("请求超时，请尝试增加超时时间或检查网络连接。")
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP错误发生：{http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"请求错误发生：{req_err}")
    except IOError as io_err:
        print(f"处理图片失败：{io_err}")
    except Exception as e:
        print(f"获取图片信息时发生未知错误：{e}")
    return None


# 判断指定OSS路径的文件是否存在
def check_file_exists_in_oss(oss_file_path):
    """
    判断指定OSS路径的文件是否存在
    Args:
        oss_file_path (str): OSS文件路径
    Returns:
        bool: 文件存在返回True，否则返回False
    """
    try:
        # 处理OSS文件路径
        oss_file_path = process_url(oss_file_path)

        # 尝试获取文件的元数据
        bucket.head_object(oss_file_path)
        # print(f"文件 {oss_file_path} 存在于 OSS 中")
        return True
    except oss2.exceptions.NoSuchKey:
        print(f"文件 {oss_file_path} 不存在于 OSS 中")
        return False
    except Exception as e:
        # 处理其他异常
        print(f"检查文件是否存在时出错：{e}")
        return False

if __name__ == '__main__':
    config = app_config.AppConfig()
    init_oss(access_key_id=config.ACCESS_KEY_ID, access_key_secret=config.ACCESS_KEY_SECRET,
             endpoint=config.ENDPOINT, bucket_name=config.BUCKET_NAME)
    oss_url = "ai-try-on/raw/images/20240929/2Xw4EN02.jpg"
    # target_config = OssConfig()
    # init_oss(target_config)
    url = generate_get_url_scale_max_side(oss_file_path=oss_url, max_side=1024)
    print(url)
