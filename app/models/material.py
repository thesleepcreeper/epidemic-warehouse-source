#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 物资与库存模型
"""
from datetime import datetime
from decimal import Decimal
from app import db


class Category(db.Model):
    """物资分类表"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, comment='分类名称')
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True, comment='上级分类')
    sort_order = db.Column(db.Integer, default=0, comment='排序')
    remark = db.Column(db.Text, comment='备注')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.now)

    parent = db.relationship('Category', remote_side=[id], backref='children')
    items = db.relationship('Material', backref='category', lazy='dynamic')

    @property
    def full_name(self):
        """显示完整分类路径"""
        if self.parent:
            return f'{self.parent.full_name} > {self.name}'
        return self.name

    def __repr__(self):
        return f'<Category {self.name}>'


class Supplier(db.Model):
    """供应商表"""
    __tablename__ = 'suppliers'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, comment='供应商名称')
    code = db.Column(db.String(50), unique=True, comment='供应商编码')
    contact_person = db.Column(db.String(64), comment='联系人')
    phone = db.Column(db.String(20), comment='联系电话')
    address = db.Column(db.String(300), comment='地址')
    remark = db.Column(db.Text, comment='备注')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')
    created_at = db.Column(db.DateTime, default=datetime.now)

    def __repr__(self):
        return f'<Supplier {self.name}>'


class Material(db.Model):
    """物资表"""
    __tablename__ = 'materials'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, index=True, comment='物资名称')
    code = db.Column(db.String(50), unique=True, comment='物资编码')
    spec = db.Column(db.String(200), comment='规格型号')
    unit = db.Column(db.String(20), nullable=False, default='个', comment='单位')
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True, comment='所属分类')
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True, comment='默认供应商')

    # 库存相关
    current_quantity = db.Column(db.Integer, default=0, comment='当前库存数量')
    warning_quantity = db.Column(db.Integer, default=0, comment='预警库存量（低于此值预警）')
    max_quantity = db.Column(db.Integer, default=0, comment='最大库存量（超出此值建议停购）')

    # 临期预警相关
    warning_days = db.Column(db.Integer, default=90, comment='临期预警天数（到期前N天预警）')
    newest_expiry_date = db.Column(db.Date, nullable=True, comment='最新入库批次的有效期至')

    # 物资信息
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), comment='单价(元)')
    storage_location = db.Column(db.String(100), comment='存放位置')
    shelf_life_days = db.Column(db.Integer, comment='保质期(天)')
    is_consumable = db.Column(db.Boolean, default=True, comment='是否为消耗品')
    remark = db.Column(db.Text, comment='备注')
    is_active = db.Column(db.Boolean, default=True, comment='是否启用')

    created_at = db.Column(db.DateTime, default=datetime.now)
    updated_at = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    supplier = db.relationship('Supplier', backref='materials')

    @property
    def stock_status(self):
        """库存状态: normal/warning/emergency/overstock"""
        if self.warning_quantity <= 0:
            return 'normal'
        if self.current_quantity <= 0:
            return 'emergency'
        if self.current_quantity <= self.warning_quantity * 0.3:
            return 'emergency'
        if self.current_quantity <= self.warning_quantity:
            return 'warning'
        if self.max_quantity > 0 and self.current_quantity >= self.max_quantity:
            return 'overstock'
        return 'normal'

    @property
    def stock_status_name(self):
        return {
            'normal': '正常',
            'warning': '预警',
            'emergency': '紧急',
            'overstock': '超储'
        }.get(self.stock_status, '未知')

    @property
    def stock_status_color(self):
        return {
            'normal': 'success',
            'warning': 'warning',
            'emergency': 'danger',
            'overstock': 'info'
        }.get(self.stock_status, 'secondary')

    @property
    def expiry_status(self):
        """临期状态: normal/warning/expired/unknown"""
        if not self.newest_expiry_date or self.warning_days <= 0:
            return 'unknown'
        from datetime import date
        today = date.today()
        days_left = (self.newest_expiry_date - today).days
        if days_left < 0:
            return 'expired'
        if days_left <= self.warning_days:
            return 'warning'
        return 'normal'

    @property
    def expiry_status_name(self):
        return {
            'normal': '正常',
            'warning': '临期预警',
            'expired': '已过期',
            'unknown': '未设置'
        }.get(self.expiry_status, '未知')

    @property
    def expiry_status_color(self):
        return {
            'normal': 'success',
            'warning': 'warning',
            'expired': 'danger',
            'unknown': 'secondary'
        }.get(self.expiry_status, 'secondary')

    @property
    def days_to_expiry(self):
        """距离过期天数，负数表示已过期"""
        if not self.newest_expiry_date:
            return None
        from datetime import date
        return (self.newest_expiry_date - date.today()).days

    def __repr__(self):
        return f'<Material {self.name}>'
