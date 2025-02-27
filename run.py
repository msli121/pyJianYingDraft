"""
@File: run.py
@Description: flask应用启动方法

@Author: lms
@Date: 2025/2/25 11:27
"""
import pythoncom

from app import create_app

app = create_app()
# 在 Flask 应用启动时初始化 COM 库
pythoncom.CoInitialize()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=7788)
