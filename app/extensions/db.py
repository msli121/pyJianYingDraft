"""
@File: db.py
@Description: 数据库管理

@Author: lms
@Date: 2025/3/3 13:34
"""
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import text

# 自定义 SQLAlchemy session 工厂，设置 expire_on_commit 为 True
Session = scoped_session(sessionmaker(expire_on_commit=True))

# 使用单个SQLAlchemy实例管理所有数据库
db = SQLAlchemy(session_options={
    'autocommit': False,
    'autoflush': True,
    'expire_on_commit': True
})
migrate = Migrate()


def add_charset_to_uri(uri):
    if uri and 'charset=' not in uri:
        if '?' in uri:
            uri = f"{uri}&charset=utf8mb4"
        else:
            uri = f"{uri}?charset=utf8mb4"
    return uri


def init_databases(app):
    # 主数据库配置，添加字符集
    main_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    main_uri = add_charset_to_uri(main_uri)
    app.config['SQLALCHEMY_DATABASE_URI'] = main_uri

    # 初始化数据库
    db.init_app(app)
    migrate.init_app(app, db)

    # 设置时区
    @app.before_request
    def set_timezone():
        # 主数据库时区设置
        db.session.execute(text('SET time_zone = "+08:00";'))
