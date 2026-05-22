#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 用户与权限模型
"""
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db, login_manager


class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True, comment='用户名')
    real_name = db.Column(db.String(64), nullable=False, comment='真实姓名')
    password_hash = db.Column(db.String(256), nullable=False, comment='密码哈希')
    role = db.Column(db.String(20), nullable=False, default='operator', comment='角色: admin/manager/operator')
    phone = db.Column(db.String(20), comment='联系电话')
    email = db.Column(db.String(120), comment='邮箱')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='创建时间')
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now, comment='更新时间')
    last_login = db.Column(db.DateTime, comment='最后登录时间')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_permission(self, permission):
        """权限检查"""
        if self.role == 'admin':
            return True
        permissions = {
            'admin': ['view', 'create', 'edit', 'delete', 'approve', 'export', 'manage_user'],
            'manager': ['view', 'create', 'edit', 'approve', 'export'],
            'operator': ['view', 'create', 'export'],
        }
        return permission in permissions.get(self.role, [])

    @property
    def role_name(self):
        return {'admin': '管理员', 'manager': '仓管员', 'operator': '操作员'}.get(self.role, self.role)

    def __repr__(self):
        return f'<User {self.username}>'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
