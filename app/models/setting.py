#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""系统设置模型"""
from datetime import datetime
from app import db


class SystemSetting(db.Model):
    """系统设置表（键值对）"""
    __tablename__ = 'system_settings'

    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True, comment='设置键')
    value = db.Column(db.Text, default='', comment='设置值')
    description = db.Column(db.String(500), comment='说明')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    def __repr__(self):
        return f'<SystemSetting {self.key}={self.value}>'


def get_setting(key, default=''):
    """获取系统设置值"""
    setting = SystemSetting.query.filter_by(key=key).first()
    return setting.value if setting else default


def set_setting(key, value, description=''):
    """设置系统设置值"""
    setting = SystemSetting.query.filter_by(key=key).first()
    if setting:
        setting.value = value
        if description:
            setting.description = description
    else:
        setting = SystemSetting(key=key, value=value, description=description)
        db.session.add(setting)
    db.session.commit()
    return setting
