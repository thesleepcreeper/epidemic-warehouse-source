#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 首页与仪表盘路由
"""
from datetime import datetime, timedelta
from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
@login_required
def index():
    """仪表盘首页"""
    from app import db
    from app.models.material import Material, Category
    from app.models.record import InboundRecord, OutboundRecord

    # 统计数据
    total_materials = Material.query.filter_by(is_active=True).count()
    total_categories = Category.query.filter_by(is_active=True).count()

    # 库存预警数量
    all_materials = Material.query.filter_by(is_active=True).all()
    warning_materials = [m for m in all_materials if m.stock_status in ('warning', 'emergency')]
    emergency_materials = [m for m in all_materials if m.stock_status == 'emergency']

    # 临期预警
    expiring_materials = [m for m in all_materials if m.expiry_status == 'warning']
    expired_materials = [m for m in all_materials if m.expiry_status == 'expired']

    # 本月出入库统计
    today = datetime.now()
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_inbound = InboundRecord.query.filter(
        InboundRecord.created_at >= month_start
    ).count()
    monthly_outbound = OutboundRecord.query.filter(
        OutboundRecord.created_at >= month_start
    ).count()

    # 待审批出库
    pending_outbounds = OutboundRecord.query.filter_by(status='pending').count()

    # 最近出入库记录
    recent_inbounds = InboundRecord.query.order_by(
        InboundRecord.created_at.desc()
    ).limit(10).all()
    recent_outbounds = OutboundRecord.query.order_by(
        OutboundRecord.created_at.desc()
    ).limit(10).all()

    return render_template('index.html',
                           total_materials=total_materials,
                           total_categories=total_categories,
                           warning_count=len(warning_materials),
                           emergency_count=len(emergency_materials),
                           warning_materials=warning_materials[:10],
                           expiring_count=len(expiring_materials),
                           expired_count=len(expired_materials),
                           expiring_materials=expiring_materials[:10],
                           monthly_inbound=monthly_inbound,
                           monthly_outbound=monthly_outbound,
                           pending_outbounds=pending_outbounds,
                           recent_inbounds=recent_inbounds,
                           recent_outbounds=recent_outbounds)
