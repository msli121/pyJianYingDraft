import logging
import os
from logging.handlers import RotatingFileHandler

from colorlog import ColoredFormatter

from app_config import BASE_DIR


def setup_logging(app):
    """根据配置初始化日志系统"""
    log_dir = os.path.join(BASE_DIR, 'log')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)

    # 清除所有现有的 handlers
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
        handler.close()

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

    # 设置根 Logger 的日志级别
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if app.config.get('LOG_TO_STDOUT', False):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.INFO)
        stream_handler.setFormatter(formatter)
        root_logger.addHandler(stream_handler)
    else:
        log_file = os.path.join(log_dir, 'app.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=50 * 1024 * 1024,  # 50MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.INFO)
        root_logger.addHandler(file_handler)

    # 禁用 Flask 默认的 logger
    app.logger.handlers.clear()
    app.logger.propagate = True  # 让 Flask logger 传播到根 logger

    # 设置 Werkzeug logger 的传播
    werkzeug_logger = logging.getLogger('werkzeug')
    werkzeug_logger.handlers.clear()
    werkzeug_logger.propagate = True

    # 设置第三方日志级别
    logging.getLogger('apscheduler').setLevel(logging.WARNING) # apscheduler
    logging.getLogger('werkzeug').setLevel(logging.INFO)  # Flask 开发服务器日志
    logging.getLogger('urllib3').setLevel(logging.WARNING)  # requests/urllib3 日志
