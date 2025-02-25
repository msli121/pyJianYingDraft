"""
@File: routes.py
@Description: 路由定义

@Author: lms
@Date: 2025/2/25 11:20
"""
from flask import Blueprint, jsonify, request

api_blueprint = Blueprint('api', __name__)


@api_blueprint.route('/api/v1/status', methods=['GET'])
def check_status():
    """服务状态检查接口"""
    return jsonify({
        "status": "ok",
        "version": "1.0.0"
    })


@api_blueprint.route('/echo', methods=['POST'])
def echo_handler():
    """数据回显接口"""
    data = request.get_json()
    return jsonify({
        "received_data": data,
        "message": "Request processed successfully"
    })
