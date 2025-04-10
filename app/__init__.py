"""
@File: __init__.py
@Description: Flask初始化

@Author: lms
@Date: 2025/2/25 09:57
"""
from flask import Flask
from flask_cors import CORS
import app_config
from app_config import AppConfig
from app.utils.oss_utils import init_oss
from app.extensions.db import init_databases
from app.logging_config import setup_logging
from app.controller.auto_clip_controller import api_blueprint
from app.task_processor import task_processor


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

    # 初始化数据库
    init_databases(app)

    # 启用 CORS
    CORS(app)

    # 初始化任务处理器
    if app.config.get('TASK_LOOP_ENABLED', False):
        app.logger.info("启动任务处理器...")
        task_processor.start()
        
        # 注册应用关闭时的清理函数
        @app.teardown_appcontext
        def cleanup(exception=None):
            task_processor.stop()

    return app
