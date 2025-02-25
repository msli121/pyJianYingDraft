"""
@File: __init__.py
@Description: Flask初始化

@Author: lms
@Date: 2025/2/25 09:57
"""
from flask import Flask

import app_config
from app_config import AppConfig
from utils.oss_utils import init_oss
from .logging_config import setup_logging
from .routes import api_blueprint


def create_app(config_class=AppConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # 初始化日志
    setup_logging(app)

    # 初始化OSS配置
    config = app_config.AppConfig()
    init_oss(access_key_id=config.ACCESS_KEY_ID, access_key_secret=config.ACCESS_KEY_SECRET,
             endpoint=config.ENDPOINT, bucket_name=config.BUCKET_NAME)

    # 注册蓝图
    app.register_blueprint(api_blueprint)

    # 初始化扩展（如数据库等）
    # initialize_extensions(app)

    return app
