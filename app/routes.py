"""
@File: routes.py
@Description: 路由定义

@Author: lms
@Date: 2025/2/25 11:20
"""
from flask import Blueprint, jsonify, request

api_blueprint = Blueprint('api', __name__)


@api_blueprint.route('/api/status', methods=['GET'])
def check_status():
    """服务状态检查接口"""
    res = {
        "code": 0,
        "msg": "success",
        "data": None,
    }
    return jsonify(res)


@api_blueprint.route('/api/auto_cut', methods=['POST'])
def jy_auto_cut():
    """数据回显接口"""
    data = request.get_json()
    return jsonify({
        "received_data": data,
        "message": "Request processed successfully"
    })
