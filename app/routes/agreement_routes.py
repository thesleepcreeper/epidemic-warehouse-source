#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 协议储备管理路由
"""
from datetime import datetime, date
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func

from app import db
from app.models.material import Material, Supplier, AgreementReserve
from app.forms import AgreementForm

agreement_bp = Blueprint('agreement', __name__, url_prefix='/agreement')


# ========== 辅助函数 ==========

def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('权限不足，仅管理员可执行此操作', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


def _build_choices(query, label_attr='name', blank_label='-- 请选择 --'):
    """构建 SelectField 选项列表"""
    items = [(0, blank_label)]
    items += [(item.id, getattr(item, label_attr, str(item))) for item in query]
    return items


def generate_agreement_no():
    """生成协议编号：XY-YYYYMMDD-RRR"""
    import random
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = str(random.randint(100, 999))
    return f'XY-{ts}-{rand}'


# ======================================================================
#  协议列表
# ======================================================================

@agreement_bp.route('/')
@login_required
def agreement_list():
    """协议储备列表（搜索、状态筛选、分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    keyword = request.args.get('keyword', '').strip()
    status_filter = request.args.get('status', '').strip()
    material_id = request.args.get('material_id', 0, type=int)

    query = AgreementReserve.query

    if keyword:
        query = query.join(AgreementReserve.material).join(AgreementReserve.supplier).filter(
            db.or_(
                AgreementReserve.agreement_no.ilike(f'%{keyword}%'),
                Material.name.ilike(f'%{keyword}%'),
                Supplier.name.ilike(f'%{keyword}%'),
                AgreementReserve.contact_person.ilike(f'%{keyword}%'),
            )
        )

    if status_filter:
        query = query.filter(AgreementReserve.status == status_filter)

    if material_id > 0:
        query = query.filter(AgreementReserve.material_id == material_id)

    query = query.order_by(AgreementReserve.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    agreements = pagination.items

    # 物资列表供筛选
    materials_list = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()

    return render_template(
        'agreement/agreement_list.html',
        agreements=agreements,
        pagination=pagination,
        keyword=keyword,
        status_filter=status_filter,
        material_id=material_id,
        materials=materials_list,
    )


# ======================================================================
#  创建协议
# ======================================================================

@agreement_bp.route('/create', methods=['GET', 'POST'])
@login_required
@admin_required
def agreement_create():
    """新增协议储备"""
    form = AgreementForm()

    materials_qs = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()
    form.material_id.choices = _build_choices(materials_qs)

    suppliers_qs = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()
    form.supplier_id.choices = _build_choices(suppliers_qs)

    if form.validate_on_submit():
        agreement_no = form.agreement_no.data.strip() if form.agreement_no.data else generate_agreement_no()

        # 检查协议编号唯一性
        existing = AgreementReserve.query.filter_by(agreement_no=agreement_no).first()
        if existing:
            flash(f'协议编号「{agreement_no}」已存在', 'danger')
            return render_template('agreement/agreement_form.html', form=form, title='新增协议')

        total_amount = (form.unit_price.data or 0) * form.agree_quantity.data

        agreement = AgreementReserve(
            agreement_no=agreement_no,
            material_id=form.material_id.data,
            supplier_id=form.supplier_id.data,
            agree_quantity=form.agree_quantity.data,
            unit_price=form.unit_price.data or 0,
            total_amount=total_amount,
            start_date=form.start_date.data,
            end_date=form.end_date.data,
            delivery_lead_days=form.delivery_lead_days.data or 7,
            contact_person=form.contact_person.data.strip() if form.contact_person.data else '',
            contact_phone=form.contact_phone.data.strip() if form.contact_phone.data else '',
            remark=form.remark.data.strip() if form.remark.data else '',
        )
        db.session.add(agreement)
        db.session.commit()
        flash(f'协议「{agreement.agreement_no}」创建成功', 'success')
        return redirect(url_for('agreement.agreement_list'))

    return render_template('agreement/agreement_form.html', form=form, title='新增协议')


# ======================================================================
#  编辑协议
# ======================================================================

@agreement_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def agreement_edit(id):
    """编辑协议储备"""
    agreement = AgreementReserve.query.get_or_404(id)
    form = AgreementForm(obj=agreement)

    materials_qs = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()
    form.material_id.choices = _build_choices(materials_qs)

    suppliers_qs = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()
    form.supplier_id.choices = _build_choices(suppliers_qs)

    # 恢复关联选择
    if form.material_id.data == 0 and agreement.material_id is not None:
        form.material_id.data = agreement.material_id
    if form.supplier_id.data == 0 and agreement.supplier_id is not None:
        form.supplier_id.data = agreement.supplier_id

    if form.validate_on_submit():
        # 检查协议编号唯一性（排除自身）
        agreement_no = form.agreement_no.data.strip()
        existing = AgreementReserve.query.filter(
            AgreementReserve.agreement_no == agreement_no,
            AgreementReserve.id != agreement.id
        ).first()
        if existing:
            flash(f'协议编号「{agreement_no}」已被其他协议使用', 'danger')
            return render_template('agreement/agreement_form.html', form=form, title='编辑协议', agreement=agreement)

        agreement.agreement_no = agreement_no
        agreement.material_id = form.material_id.data
        agreement.supplier_id = form.supplier_id.data
        agreement.agree_quantity = form.agree_quantity.data
        agreement.unit_price = form.unit_price.data or 0
        agreement.total_amount = (form.unit_price.data or 0) * form.agree_quantity.data
        agreement.start_date = form.start_date.data
        agreement.end_date = form.end_date.data
        agreement.delivery_lead_days = form.delivery_lead_days.data or 7
        agreement.contact_person = form.contact_person.data.strip() if form.contact_person.data else ''
        agreement.contact_phone = form.contact_phone.data.strip() if form.contact_phone.data else ''
        agreement.remark = form.remark.data.strip() if form.remark.data else ''
        db.session.commit()
        flash(f'协议「{agreement.agreement_no}」更新成功', 'success')
        return redirect(url_for('agreement.agreement_list'))

    return render_template('agreement/agreement_form.html', form=form, title='编辑协议', agreement=agreement)


# ======================================================================
#  协议详情
# ======================================================================

@agreement_bp.route('/<int:id>')
@login_required
def agreement_detail(id):
    """协议详情"""
    agreement = AgreementReserve.query.get_or_404(id)
    return render_template('agreement/agreement_detail.html', agreement=agreement)


# ======================================================================
#  终止协议
# ======================================================================

@agreement_bp.route('/<int:id>/terminate', methods=['POST'])
@login_required
@admin_required
def agreement_terminate(id):
    """终止协议"""
    agreement = AgreementReserve.query.get_or_404(id)
    if agreement.status != 'active':
        flash(f'协议「{agreement.agreement_no}」当前状态为「{agreement.status_name}」，无法终止', 'warning')
        return redirect(url_for('agreement.agreement_list'))

    agreement.status = 'terminated'
    db.session.commit()
    flash(f'协议「{agreement.agreement_no}」已终止', 'success')
    return redirect(url_for('agreement.agreement_list'))


# ======================================================================
#  储备总览报表
# ======================================================================

@agreement_bp.route('/reserve-report')
@login_required
def reserve_report():
    """储备总览：实物储备 + 协议储备合并报表"""
    # 获取所有活跃物资
    materials = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()

    report_data = []
    total_physical = 0
    total_agreement = 0
    total_reserve = 0
    active_agreements_count = 0

    for m in materials:
        physical_qty = m.current_quantity or 0
        # 生效中的协议储备总量
        agreement_qty_result = db.session.query(
            func.coalesce(func.sum(AgreementReserve.agree_quantity), 0)
        ).filter(
            AgreementReserve.material_id == m.id,
            AgreementReserve.status == 'active',
            AgreementReserve.end_date >= date.today(),
        ).scalar()
        agreement_qty = int(agreement_qty_result) if agreement_qty_result else 0

        total_qty = physical_qty + agreement_qty
        report_data.append({
            'material': m,
            'physical_quantity': physical_qty,
            'agreement_quantity': agreement_qty,
            'total_quantity': total_qty,
        })
        total_physical += physical_qty
        total_agreement += agreement_qty
        total_reserve += total_qty

    # 生效中协议数量
    active_agreements_count = AgreementReserve.query.filter(
        AgreementReserve.status == 'active',
        AgreementReserve.end_date >= date.today(),
    ).count()

    return render_template(
        'agreement/reserve_report.html',
        report_data=report_data,
        total_physical=total_physical,
        total_agreement=total_agreement,
        total_reserve=total_reserve,
        active_agreements_count=active_agreements_count,
    )
