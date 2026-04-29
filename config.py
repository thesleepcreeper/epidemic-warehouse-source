#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 配置文件
单机运行，数据保存于本地 SQLite 文件
"""
import os
import sys


def get_base_dir():
    """获取应用根目录，兼容 PyInstaller 打包后的路径"""
    if getattr(sys, 'frozen', False):
        # 打包后的 exe 运行时
        if sys.platform == 'darwin':
            # macOS .app 包: Contents/MacOS/ 的上级的上级
            base = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
        else:
            # Windows/Linux exe
            base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    return base


def get_data_dir():
    """获取数据目录（存数据库和导出文件），放在可执行文件旁边"""
    base = get_base_dir()
    data_dir = os.path.join(base, 'data')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir


BASE_DIR = get_base_dir()


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'epi-wh-secret-key-change-in-prod-2026')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(get_data_dir(), 'warehouse.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True

    # 分页配置
    ITEMS_PER_PAGE = 20

    # 库存预警阈值
    WARNING_THRESHOLD = 1.0
    LOW_STOCK_THRESHOLD = 0.3

    # 审批相关
    APPROVAL_REQUIRED = True

    # 文件上传
    UPLOAD_FOLDER = os.path.join(get_data_dir(), 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Excel 导出路径
    EXPORT_FOLDER = os.path.join(get_data_dir(), 'exports')
