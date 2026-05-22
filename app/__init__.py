#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - Flask 应用工厂
兼容 PyInstaller 打包环境
"""
import os
import sys
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
login_manager = LoginManager()
csrf = CSRFProtect()


def resource_path(relative_path):
    """获取资源路径，兼容 PyInstaller _MEIPASS"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    return os.path.join(base, relative_path)


def create_app(config_class=None):
    # 关键：告诉 Flask 模板和静态文件在打包后的 _MEIPASS 中
    template_dir = resource_path('app/templates')
    static_dir = resource_path('app/static')

    app = Flask(__name__,
                template_folder=template_dir,
                static_folder=static_dir,
                static_url_path='/static')

    from config import Config
    from config import get_data_dir
    app.config.from_object(config_class or Config)

    # 确保数据目录存在
    data_dir = get_data_dir()
    os.makedirs(os.path.join(data_dir, 'uploads'), exist_ok=True)
    os.makedirs(os.path.join(data_dir, 'exports'), exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录'
    login_manager.login_message_category = 'warning'

    # 注册蓝图（去掉各蓝图自己的 template_folder，使用 app 的默认路径）
    from app.routes.auth_routes import auth_bp
    from app.routes.inventory_routes import inventory_bp
    from app.routes.record_routes import record_bp
    from app.routes.report_routes import report_bp
    from app.routes.main_routes import main_bp
    from app.routes.setting_routes import setting_bp
    from app.routes.agreement_routes import agreement_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(inventory_bp, url_prefix='/inventory')
    app.register_blueprint(record_bp, url_prefix='/record')
    app.register_blueprint(report_bp, url_prefix='/report')
    app.register_blueprint(main_bp)
    app.register_blueprint(setting_bp)
    app.register_blueprint(agreement_bp)

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('common/404.html'), 404

    @app.errorhandler(500)
    def internal_error(e):
        db.session.rollback()
        from flask import render_template
        return render_template('common/500.html'), 500

    # 上下文处理器（注入单位名称等全局变量）
    @app.context_processor
    def inject_globals():
        from flask_login import current_user
        from app.models.setting import get_setting
        unit_name = get_setting('unit_name', '')
        unit_short = get_setting('unit_short', '') or unit_name[:20] if unit_name else ''
        return dict(
            current_user=current_user,
            unit_name=unit_name,
            unit_short=unit_short or unit_name,
        )

    return app
