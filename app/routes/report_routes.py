#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 报表统计路由
"""
from datetime import datetime, timedelta
import os

from flask import Blueprint, render_template, redirect, url_for, flash, request, send_from_directory, current_app
from flask_login import login_required, current_user
import pandas as pd

from app import db
from app.models.material import Material, Category, Supplier
from app.models.record import InboundRecord, OutboundRecord

report_bp = Blueprint(
    'report', __name__,
    url_prefix='/report',
)


# ========== 辅助函数 ==========

def _get_stock_dataframe():
    """生成库存总表 DataFrame"""
    materials = Material.query.filter_by(is_active=True) \
        .order_by(Material.category_id.asc(), Material.name.asc()) \
        .all()

    data = []
    for m in materials:
        stock_value = round(m.current_quantity * float(m.unit_price or 0), 2)
        data.append({
            '物资编码': m.code or '',
            '物资名称': m.name,
            '规格型号': m.spec or '',
            '单位': m.unit,
            '分类': m.category.full_name if m.category else '',
            '当前库存': m.current_quantity,
            '预警库存': m.warning_quantity,
            '最大库存': m.max_quantity,
            '单价(元)': float(m.unit_price or 0),
            '库存价值(元)': stock_value,
            '库存状态': m.stock_status_name,
            '存放位置': m.storage_location or '',
            '供应商': m.supplier.name if m.supplier else '',
        })

    return pd.DataFrame(data)


def _get_summary_dataframe(model, freq='D'):
    """生成出入库统计 DataFrame（按日/月/年聚合）"""
    now = datetime.now()

    if freq == 'D':
        # 最近30天按日统计
        start_date = now - timedelta(days=30)
        date_format = '%Y-%m-%d'
        date_label = '日期'
    elif freq == 'M':
        # 最近12个月按月统计
        start_date = now - timedelta(days=365)
        date_format = '%Y-%m'
        date_label = '月份'
    elif freq == 'Y':
        # 所有年份按年统计
        start_date = datetime(2000, 1, 1)
        date_format = '%Y'
        date_label = '年份'
    else:
        start_date = now - timedelta(days=30)
        date_format = '%Y-%m-%d'
        date_label = '日期'

    records = model.query \
        .filter(model.created_at >= start_date) \
        .order_by(model.created_at.asc()) \
        .all()

    summary = {}
    for r in records:
        key = r.created_at.strftime(date_format)
        if key not in summary:
            summary[key] = {'count': 0, 'total_quantity': 0, 'total_amount': 0.0}
        summary[key]['count'] += 1
        summary[key]['total_quantity'] += r.quantity
        summary[key]['total_amount'] += float(r.total_amount or 0)

    data = []
    for date_key in sorted(summary.keys()):
        s = summary[date_key]
        data.append({
            date_label: date_key,
            '单据数量': s['count'],
            '总数量': s['total_quantity'],
            '总金额(元)': round(s['total_amount'], 2),
        })

    return pd.DataFrame(data)


def _get_inventory_value_dataframe():
    """生成库存价值统计 DataFrame（按分类汇总）"""
    categories = Category.query.filter_by(is_active=True) \
        .order_by(Category.sort_order.asc()) \
        .all()

    data = []
    total_value = 0.0
    for cat in categories:
        materials = Material.query.filter_by(category_id=cat.id, is_active=True).all()
        if not materials:
            continue
        cat_quantity = sum(m.current_quantity for m in materials)
        cat_value = sum(m.current_quantity * float(m.unit_price or 0) for m in materials)
        total_value += cat_value
        data.append({
            '分类': cat.full_name,
            '物资种类': len(materials),
            '总库存数量': cat_quantity,
            '总库存价值(元)': round(cat_value, 2),
            '占比(%)': 0.0,  # 计算完整表后再填
        })

    # 计算占比
    if total_value > 0 and data:
        for d in data:
            d['占比(%)'] = round(d['总库存价值(元)'] / total_value * 100, 2)

    df = pd.DataFrame(data)
    if not df.empty:
        # 添加合计行
        total_row = {
            '分类': '合计',
            '物资种类': df['物资种类'].sum(),
            '总库存数量': df['总库存数量'].sum(),
            '总库存价值(元)': round(df['总库存价值(元)'].sum(), 2),
            '占比(%)': 100.0,
        }
        df = pd.concat([df, pd.DataFrame([total_row])], ignore_index=True)

    return df


def _ensure_export_folder():
    """确保导出目录存在"""
    export_folder = current_app.config.get('EXPORT_FOLDER',
                                           os.path.join(current_app.root_path, 'data', 'exports'))
    os.makedirs(export_folder, exist_ok=True)
    return export_folder


# ======================================================================
#  库存报表
# ======================================================================

@report_bp.route('/stock')
@login_required
def stock():
    """库存总表（所有物资库存状态）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    keyword = request.args.get('keyword', '').strip()
    category_id = request.args.get('category_id', 0, type=int)
    stock_status = request.args.get('stock_status', '')

    query = Material.query.filter_by(is_active=True)

    if keyword:
        query = query.filter(
            db.or_(
                Material.name.ilike(f'%{keyword}%'),
                Material.code.ilike(f'%{keyword}%'),
                Material.spec.ilike(f'%{keyword}%'),
            )
        )

    if category_id > 0:
        query = query.filter(Material.category_id == category_id)

    query = query.order_by(Material.category_id.asc(), Material.name.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    materials_list = pagination.items

    # 在 Python 层面按库存状态筛选
    if stock_status:
        materials_list = [m for m in materials_list if m.stock_status == stock_status]

    categories = Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc()).all()

    return render_template(
        'report/stock.html',
        materials=materials_list,
        pagination=pagination,
        keyword=keyword,
        category_id=category_id,
        stock_status=stock_status,
        categories=categories,
    )


@report_bp.route('/stock/warnings')
@login_required
def stock_warnings():
    """库存预警列表（低于预警量的物资）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    # 查询预警库存量大于 0 且当前库存 <= 预警库存的物资
    query = Material.query.filter(
        Material.is_active.is_(True),
        Material.warning_quantity > 0,
        Material.current_quantity <= Material.warning_quantity,
    ).order_by(
        (Material.current_quantity * 1.0 / Material.warning_quantity).asc(),
        Material.name.asc(),
    )

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    materials_list = pagination.items

    return render_template(
        'report/stock_warnings.html',
        materials=materials_list,
        pagination=pagination,
    )


@report_bp.route('/stock/export')
@login_required
def stock_export():
    """导出库存总表为 Excel"""
    if not current_user.has_permission('export'):
        flash('权限不足，无法导出数据', 'danger')
        return redirect(url_for('report.stock'))

    df = _get_stock_dataframe()

    if df.empty:
        flash('没有可导出的库存数据', 'warning')
        return redirect(url_for('report.stock'))

    export_folder = _ensure_export_folder()
    filename = f'stock_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    filepath = os.path.join(export_folder, filename)

    # 写入 Excel
    with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='库存总表', index=False)
        # 调整列宽
        worksheet = writer.sheets['库存总表']
        for col_idx, col in enumerate(df.columns, 1):
            max_len = max(len(str(col)), df[col].astype(str).str.len().max() if len(df) > 0 else 0)
            adjusted_width = min(max_len + 4, 40)
            worksheet.column_dimensions[chr(64 + col_idx) if col_idx <= 26 else 'A'].width = adjusted_width

    flash(f'库存总表已导出：{filename}', 'success')
    return send_from_directory(
        export_folder,
        filename,
        as_attachment=True,
        download_name=filename,
    )


# ======================================================================
#  出入库统计报表
# ======================================================================

@report_bp.route('/inbound-summary')
@login_required
def inbound_summary():
    """入库统计（按日/月/年聚合）"""
    freq = request.args.get('freq', 'D').upper()
    if freq not in ('D', 'M', 'Y'):
        freq = 'D'

    df = _get_summary_dataframe(InboundRecord, freq)

    freq_name = {'D': '日', 'M': '月', 'Y': '年'}.get(freq, '日')

    table_data = df.to_dict('records') if not df.empty else []

    return render_template(
        'report/inbound_summary.html',
        table_data=table_data,
        freq=freq,
        freq_name=freq_name,
        total_count=len(table_data),
    )


@report_bp.route('/outbound-summary')
@login_required
def outbound_summary():
    """出库统计（按日/月/年聚合）"""
    freq = request.args.get('freq', 'D').upper()
    if freq not in ('D', 'M', 'Y'):
        freq = 'D'

    df = _get_summary_dataframe(OutboundRecord, freq)

    freq_name = {'D': '日', 'M': '月', 'Y': '年'}.get(freq, '日')

    table_data = df.to_dict('records') if not df.empty else []

    return render_template(
        'report/outbound_summary.html',
        table_data=table_data,
        freq=freq,
        freq_name=freq_name,
        total_count=len(table_data),
    )


# ======================================================================
#  库存价值统计
# ======================================================================

@report_bp.route('/inventory-value')
@login_required
def inventory_value():
    """库存价值统计（按分类汇总）"""
    df = _get_inventory_value_dataframe()

    table_data = df.to_dict('records') if not df.empty else []

    total_value = 0.0
    for d in table_data:
        if d['分类'] == '合计':
            total_value = d['总库存价值(元)']
            break

    return render_template(
        'report/inventory_value.html',
        table_data=table_data,
        total_value=total_value,
    )
