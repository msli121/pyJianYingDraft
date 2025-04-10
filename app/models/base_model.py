"""
@File: base_model.py
@Description: 基础数据库模型

@Author: lms
@Date: 2025/3/3 14:27
"""
import logging
from datetime import datetime
from sqlalchemy import text

from sqlalchemy import Column, DateTime
from sqlalchemy import and_
from sqlalchemy.sql import func

from app.extensions.db import db

logger = logging.getLogger(__name__)


def parse_filter_params(cls, filters):
    """
    解析过滤参数
    :cls : 数据库模型类
    :param filters: 过滤参数字典，格式为 {column: (op, value)}
    """
    filter_conditions = []
    if not filters:
        return filter_conditions
    for column, (op, value) in filters.items():
        if hasattr(cls, column):
            if op == 'eq':
                filter_conditions.append(getattr(cls, column) == value)
            elif op == 'ne':
                filter_conditions.append(getattr(cls, column) != value)
            elif op == 'like':
                filter_conditions.append(getattr(cls, column).like(f"%{value}%"))
            elif op == 'in':
                filter_conditions.append(getattr(cls, column).in_(value))
            elif op == 'not in':
                filter_conditions.append(~getattr(cls, column).in_(value))
            elif op == 'gt':
                filter_conditions.append(getattr(cls, column) > value)
            elif op == 'lt':
                filter_conditions.append(getattr(cls, column) < value)
            elif op == 'ge':
                filter_conditions.append(getattr(cls, column) >= value)
            elif op == 'le':
                filter_conditions.append(getattr(cls, column) <= value)
            elif op == 'between':
                if not isinstance(value, (list, tuple)) or len(value) != 2:
                    raise ValueError("The value for 'between' operation should be a list or tuple of two elements.")
                start, end = value
                filter_conditions.append(getattr(cls, column).between(start, end))
            else:
                raise ValueError(f"Unsupported operation: {op}")
        else:
            raise ValueError(f"Filter column {column} does not exist.")
    return filter_conditions


def parse_orders_params(cls, query, orders=None):
    """
    解析排序参数
    :param cls: 数据库模型类
    :param query: 查询对象
    :param orders: 排序参数列表，格式为 [{'key': column, 'value': direction}]
    """
    if not query or not cls:
        return query
    if not orders:
        query = query.order_by(cls.id.desc())
        return query
    for order_item in orders:
        column = order_item.get('key')
        direction = order_item.get('value')
        if hasattr(cls, column):
            if direction == 'desc':
                query = query.order_by(getattr(cls, column).desc())
            elif direction == 'asc':
                query = query.order_by(getattr(cls, column).asc())
            else:
                raise ValueError(f"不支持的排序方向: {direction}。只能是 'asc' 或 'desc'。")
        else:
            raise ValueError(f"排序字段 {column} 不存在。")
    return query


class BaseModel(db.Model):
    # 表示这是一个抽象基类，不会在数据库中创建对应的表
    __abstract__ = True

    create_time = Column(DateTime(timezone=True), server_default=func.now(), comment='创建时间')
    update_time = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now(), comment='更新时间')

    @staticmethod
    def execute_raw_sql(sql):
        try:
            db.session.flush()
            result = db.session.execute(text(sql))
            columns = result.keys()
            rows = [dict(zip(columns, row)) for row in result.fetchall()]
            return rows
        except Exception as e:
            logger.error(f"SQL execution error: {e}")
            return []

    def to_dict(self):
        """Convert models instance to dictionary with formatted datetime."""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.strftime('%Y-%m-%d %H:%M:%S')
            result[column.name] = value
        return result

    @classmethod
    def create(cls, **kwargs):
        """
        创建新的数据记录到第一个数据库
        :param kwargs: 创建记录所需的字段和值
        :return: 创建后的数据对象的字典形式
        """
        try:
            new_obj = cls(**kwargs)
            db.session.add(new_obj)
            db.session.commit()
            return new_obj.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def get_by_id(cls, id):
        """
        根据 ID 从第一个数据库查询数据
        :param id: 数据的 ID
        :return: 查询到的数据对象的字典形式
        """
        obj = db.session.query(cls).get(id)
        return obj.to_dict() if obj else None

    @classmethod
    def get_by_ids(cls, ids):
        """
        根据 ID 列表从第一个数据库查询数据
        :param ids: 数据的 ID 列表
        :return: 查询到的数据对象的字典形式列表
        """
        objs = db.session.query(cls).filter(cls.id.in_(ids)).order_by(cls.id.desc()).all()
        return [obj.to_dict() for obj in objs]

    @classmethod
    def get_all(cls, ):
        """Retrieve all BizPlatformUser records"""
        objs = db.session.query(cls).order_by(cls.id.desc()).all()
        return [obj.to_dict() for obj in objs]

    @classmethod
    def update(cls, id, **data):
        """
        根据 ID 更新第一个数据库的数据
        :param id: 要更新记录的 ID
        :param data: 要更新的数据字典
        :return: 更新后的数据对象的字典形式
        """
        try:
            obj = db.session.query(cls).get(id)
            if not obj:
                return None
            for key, value in data.items():
                setattr(obj, key, value)
            obj.update_time = datetime.now()  # 更新 update_time 字段
            db.session.commit()
            return obj.to_dict()
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def delete(cls, id):
        """
        根据 ID 从第一个数据库删除数据
        :param id: 要删除记录的 ID
        :return: None
        """
        try:
            rows_deleted = db.session.query(cls).filter_by(id=id).delete()
            if rows_deleted > 0:
                db.session.commit()
            else:
                # 如果没有删除任何行，可选择不提交事务
                db.session.rollback()
            return rows_deleted
        except Exception as e:
            db.session.rollback()
            raise e

    @classmethod
    def query_with_filters_and_pagination(cls, page_num, page_size, filters, orders=None):
        """
        带有过滤条件和分页的查询方法
        :param page_num: 页码
        :param page_size: 每页数量
        :param filters: 过滤条件字典，格式为 {column: (op, value)}
        :param orders: 排序条件列表，格式为 [{'key': column, 'value': direction}]
        :return: 总记录数和当前页记录的字典列表
        """
        # db.session.expire_all()
        db.session.flush()
        query = db.session.query(cls)
        # 构建过滤条件
        filter_conditions = parse_filter_params(cls, filters)
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))
        # 处理排序字段
        query = parse_orders_params(cls, query, orders)
        # 分页查询
        pagination = query.paginate(page=page_num, per_page=page_size)
        # 格式化结果
        results = [item.to_dict() for item in pagination.items]
        return pagination.total, results

    @classmethod
    def update_records_with_filters(cls, filters, update_fields):
        """
        根据指定的过滤条件和待更新字段，更新数据库中的记录。
        :param filters: 过滤条件字典，键为列名，值为一个元组 (操作符, 值)。
                        操作符可以是 'eq'（等于）、'ne'（不等于）、'like'（模糊匹配）、'in'（包含）。
        :param update_fields: 待更新字段的字典，键为列名，值为新的值。
        :return: 更新的记录数量。
        """
        # db.session.expire_all()
        db.session.flush()
        query = db.session.query(cls)
        # 构建过滤条件
        filter_conditions = parse_filter_params(cls, filters)
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))
        # 更新记录
        records_updated = query.update(update_fields, synchronize_session=False)
        db.session.commit()

        return records_updated

    @classmethod
    def count_records_with_filters(cls, filters):
        """
        统计符合指定过滤条件的记录数量。

        :param filters: 过滤条件字典，键为列名，值为一个元组 (操作符, 值)。
                        示例: {'status': ('eq', 1), 'type': ('ne', 'text')}
        :return: 符合条件的记录数量。
        """
        # db.session.expire_all()
        db.session.flush()
        query = db.session.query(cls)
        # 构建过滤条件
        filter_conditions = parse_filter_params(cls, filters)
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))
        # 返回符合过滤条件的记录数量
        return query.count()

    @classmethod
    def delete_records_with_filters(cls, filters):
        """
        删除满足指定条件的记录。

        :param filters: 过滤条件字典，key 为列名，value 为包含操作符和值的元组 (operation, value)，
                        其中操作符可以是 'eq'（等于）、'ne'（不等于）、'like'（模糊匹配）、'in'（在列表中）。
                        例如：{'status': ('eq', 1), 'tag_code': ('ne', '001')}
        :return: 被删除的记录数量。
        """
        # 检查 filters 是否为空或 None，避免误删除
        if not filters:
            return 0
        db.session.flush()
        query = db.session.query(cls)
        # 应用过滤条件
        filter_conditions = parse_filter_params(cls, filters)
        if filter_conditions:
            query = query.filter(and_(*filter_conditions))
        # 批量删除记录
        num_deleted = query.delete(synchronize_session=False)
        db.session.commit()
        return num_deleted
