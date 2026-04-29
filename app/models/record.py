#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 出入库记录与审批模型
"""
from datetime import datetime
from decimal import Decimal
from app import db


class InboundRecord(db.Model):
    """入库记录表"""
    __tablename__ = 'inbound_records'

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(64), unique=True, nullable=False, comment='入库单号')
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False, comment='物资')
    quantity = db.Column(db.Integer, nullable=False, comment='入库数量')
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), comment='入库单价')
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), comment='入库总金额')
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=True, comment='供应商')
    batch_no = db.Column(db.String(64), comment='批次号')
    production_date = db.Column(db.Date, comment='生产日期')
    expiry_date = db.Column(db.Date, comment='有效期至')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='操作人')
    remark = db.Column(db.Text, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='入库时间')

    material = db.relationship('Material', backref='inbound_records')
    supplier = db.relationship('Supplier', backref='inbound_records')
    operator = db.relationship('User', backref='inbound_records', foreign_keys=[operator_id])

    def __repr__(self):
        return f'<Inbound {self.order_no}>'


class OutboundRecord(db.Model):
    """出库记录表"""
    __tablename__ = 'outbound_records'

    id = db.Column(db.Integer, primary_key=True)
    order_no = db.Column(db.String(64), unique=True, nullable=False, comment='出库单号')
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False, comment='物资')
    quantity = db.Column(db.Integer, nullable=False, comment='出库数量')
    unit_price = db.Column(db.Numeric(10, 2), default=Decimal('0.00'), comment='出库单价')
    total_amount = db.Column(db.Numeric(12, 2), default=Decimal('0.00'), comment='出库总金额')
    recipient = db.Column(db.String(100), comment='领用单位/人')
    purpose = db.Column(db.String(500), comment='用途说明')
    batch_no = db.Column(db.String(64), comment='批次号')

    # 审批状态
    status = db.Column(db.String(20), nullable=False, default='pending',
                       comment='状态: pending/approved/rejected/cancelled')
    applicant_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='申请人')
    approver_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='审批人')
    approve_remark = db.Column(db.Text, comment='审批意见')
    approved_at = db.Column(db.DateTime, comment='审批时间')

    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, comment='出库操作人')
    remark = db.Column(db.Text, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='申请时间')

    material = db.relationship('Material', backref='outbound_records')
    applicant = db.relationship('User', backref='outbound_applications', foreign_keys=[applicant_id])
    approver = db.relationship('User', backref='outbound_approvals', foreign_keys=[approver_id])
    operator = db.relationship('User', backref='outbound_operations', foreign_keys=[operator_id])

    @property
    def status_name(self):
        return {
            'pending': '待审批',
            'approved': '已通过',
            'rejected': '已驳回',
            'cancelled': '已取消'
        }.get(self.status, self.status)

    @property
    def status_color(self):
        return {
            'pending': 'warning',
            'approved': 'success',
            'rejected': 'danger',
            'cancelled': 'secondary'
        }.get(self.status, 'secondary')

    def __repr__(self):
        return f'<Outbound {self.order_no} [{self.status}]>'


class InventoryCheck(db.Model):
    """库存盘点记录"""
    __tablename__ = 'inventory_checks'

    id = db.Column(db.Integer, primary_key=True)
    check_no = db.Column(db.String(64), unique=True, nullable=False, comment='盘点单号')
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False, comment='物资')
    book_quantity = db.Column(db.Integer, nullable=False, comment='账面数量')
    actual_quantity = db.Column(db.Integer, nullable=False, comment='实际数量')
    difference = db.Column(db.Integer, nullable=False, comment='差异数量')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='盘点人')
    remark = db.Column(db.Text, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now, comment='盘点时间')

    material = db.relationship('Material', backref='inventory_checks')
    operator = db.relationship('User', backref='inventory_checks')

    def __repr__(self):
        return f'<InventoryCheck {self.check_no}>'


class YearEndClose(db.Model):
    """年度结转记录"""
    __tablename__ = 'year_end_closes'

    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.Integer, nullable=False, comment='结转年份')
    close_date = db.Column(db.DateTime, default=datetime.now, comment='结转时间')
    operator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, comment='操作人')
    summary_json = db.Column(db.Text, comment='结转摘要(JSON格式)')
    total_materials = db.Column(db.Integer, default=0, comment='结转物资总数')
    total_quantity = db.Column(db.Integer, default=0, comment='结转总数量')
    expired_count = db.Column(db.Integer, default=0, comment='过期物资数量')
    remark = db.Column(db.Text, comment='备注')
    created_at = db.Column(db.DateTime, default=datetime.now)

    operator = db.relationship('User', backref='year_end_closes')
    snapshots = db.relationship('YearEndStockSnapshot', backref='year_end_close',
                                 lazy='dynamic', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<YearEndClose {self.year}>'


class YearEndStockSnapshot(db.Model):
    """年度结转库存快照"""
    __tablename__ = 'year_end_stock_snapshots'

    id = db.Column(db.Integer, primary_key=True)
    year_end_close_id = db.Column(db.Integer, db.ForeignKey('year_end_closes.id'),
                                  nullable=False, comment='结转记录ID')
    material_id = db.Column(db.Integer, db.ForeignKey('materials.id'), nullable=False, comment='物资ID')
    name = db.Column(db.String(200), nullable=False, comment='物资名称')
    code = db.Column(db.String(50), comment='物资编码')
    spec = db.Column(db.String(200), comment='规格型号')
    unit = db.Column(db.String(20), comment='单位')
    category_name = db.Column(db.String(100), comment='分类名称')
    quantity_before = db.Column(db.Integer, default=0, comment='结转前库存数量')
    unit_price = db.Column(db.Numeric(10, 2), default=0, comment='单价')
    total_value = db.Column(db.Numeric(12, 2), default=0, comment='库存价值')
    expiry_date = db.Column(db.Date, comment='有效期至')
    status = db.Column(db.String(20), default='normal', comment='状态: normal/warning/expired')
    storage_location = db.Column(db.String(100), comment='存放位置')

    material = db.relationship('Material', backref='year_end_snapshots')

    def __repr__(self):
        return f'<YearEndStockSnapshot {self.name} x{self.quantity_before}>'
