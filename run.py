"""
@File: run.py
@Description: flask应用启动方法

@Author: lms
@Date: 2025/2/25 11:27
"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    port = 7788
    # port = 8899
    app.run(host='0.0.0.0', port=port)
