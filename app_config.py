"""
@File: app_config.py.py
@Description: 

@Author: lms
@Date: 2025/2/25 09:59
"""
import os

from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 根据环境加载不同文件
env = os.environ.get('FLASK_ENV', 'dev')
env_files = {
    'dev': '.env',
    'prod': '.env.prod',
}
load_dotenv(dotenv_path=os.path.join(BASE_DIR, env_files.get(env, '..env')))


def parse_boolean(value):
    """将字符串或特定值解析为布尔类型。

    支持解析：True/False（不区分大小写）、1/0、'true'/'false'等字符串。
    若输入非字符串但可转换为布尔类型（如直接传入True/False），直接返回。
    其他无法识别的值会抛出ValueError。
    """
    if isinstance(value, bool):
        return value
    s = str(value).strip().lower()
    boolean_map = {
        'true': True,
        'false': False,
        '1': True,
        '0': False,
        't': True,
        'f': False,
        'yes': True,  # 可选扩展
        'no': False,  # 可选扩展
    }
    if s in boolean_map:
        return boolean_map[s]
    else:
        # raise ValueError(f"无法解析为布尔值: {repr(value)}")
        return False


class AppConfig:
    # 日志配置
    LOG_TO_STDOUT = parse_boolean(os.getenv('LOG_TO_STDOUT', True))
    # 阿里云OSS配置
    # OSS endpoint，建议选择与Bucket在同一个地域的Endpoint
    ENDPOINT = os.getenv('ENDPOINT')
    # Bucket名称
    BUCKET_NAME = os.getenv('BUCKET_NAME')
    # 阿里云AccessKeyId
    ACCESS_KEY_ID = os.getenv('ACCESS_KEY_ID')
    # 阿里云AccessKeySecret
    ACCESS_KEY_SECRET = os.getenv('ACCESS_KEY_SECRET')


if __name__ == '__main__':
    t = parse_boolean(True)
    print(t)
