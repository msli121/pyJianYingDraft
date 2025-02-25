"""
@File: logging_config.py
@Description: 日志统一处理

@Author: lms
@Date: 2025/2/25 10:02
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from colorlog import ColoredFormatter

from app_config import BASE_DIR


def setup_logging(app):
    """根据配置初始化日志系统"""

    log_dir = os.path.join(BASE_DIR, 'log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)  # 使用exist_ok避免竞态条件

    # 清除默认handler
    for handler in app.logger.handlers[:]:
        app.logger.removeHandler(handler)
        handler.close()  # 显式关闭（双重保障）

    # 统一格式
    log_format = '%(log_color)s%(asctime)s %(levelname)s: %(message)s [in %(filename)s:%(lineno)d]'
    formatter = ColoredFormatter(
        log_format,
        datefmt='%Y-%m-%d %H:%M:%S',
        reset=True,
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    # 设置根 Logger 的日志级别为 INFO
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    # 清空根 Logger 原有的处理器
    root_logger.handlers.clear()

    if app.config.get('LOG_TO_STDOUT', False):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        app.logger.addHandler(stream_handler)
        root_logger.addHandler(stream_handler)
    else:
        # 确保日志文件路径正确指向 logs 目录
        log_file = os.path.join(log_dir, 'app.log')
        # 修改 maxBytes 参数为 50MB（50 * 1024 * 1024）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        root_logger.addHandler(file_handler)

    # 设置日志级别
    app.logger.setLevel(logging.INFO)
    app.logger.propagate = False
