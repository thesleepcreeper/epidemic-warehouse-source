#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 出入库记录与审批路由
"""
from datetime import datetime, date
import random
import io
import json

from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, Response, send_file
from flask_login import login_required, current_user

from app import db
from app.models.record import InboundRecord, OutboundRecord, YearEndClose, YearEndStockSnapshot
from app.models.material import Material, Supplier, Category
from app.models.user import User
from app.forms import InboundForm, OutboundForm, ApproveForm

record_bp = Blueprint(
    'record', __name__,
    url_prefix='/record',
)


# ========== 辅助函数 ==========

def generate_order_no(prefix='RK'):
    """生成出入库单号"""
    return prefix + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10, 99))


def _build_material_choices():
    """构建物资下拉选择列表"""
    items = [(0, '-- 请选择物资 --')]
    materials = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()
    items += [(m.id, f'{m.name} ({m.spec or "-"}) - 库存: {m.current_quantity}{m.unit}') for m in materials]
    return items


def _build_supplier_choices():
    """构建供应商下拉选择列表"""
    items = [(0, '-- 请选择供应商 --')]
    items += [(s.id, s.name) for s in Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()]
    return items


# ======================================================================
#  入库管理
# ======================================================================

@record_bp.route('/inbounds')
@login_required
def inbounds():
    """入库记录列表（分页、日期筛选）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    material_id = request.args.get('material_id', 0, type=int)

    query = InboundRecord.query

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(InboundRecord.created_at >= dt_from)
        except ValueError:
            flash('起始日期格式无效，请使用 YYYY-MM-DD 格式', 'warning')

    if date_to:
        try:
            dt_to = datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = query.filter(InboundRecord.created_at <= dt_to)
        except ValueError:
            flash('截止日期格式无效，请使用 YYYY-MM-DD 格式', 'warning')

    if material_id > 0:
        query = query.filter(InboundRecord.material_id == material_id)

    query = query.order_by(InboundRecord.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items

    # 物资列表供筛选
    materials = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()

    return render_template(
        'record/inbounds.html',
        records=records,
        pagination=pagination,
        date_from=date_from,
        date_to=date_to,
        material_id=material_id,
        materials=materials,
    )


@record_bp.route('/inbound/create', methods=['GET', 'POST'])
@login_required
def inbound_create():
    """新建入库（成功后更新材料 current_quantity）"""
    form = InboundForm()
    form.material_id.choices = _build_material_choices()
    form.supplier_id.choices = _build_supplier_choices()

    if form.validate_on_submit():
        material = Material.query.get_or_404(form.material_id.data)

        quantity = form.quantity.data
        unit_price = form.unit_price.data or 0
        total_amount = round(quantity * unit_price, 2)

        order_no = generate_order_no('RK')

        record = InboundRecord(
            order_no=order_no,
            material_id=material.id,
            quantity=quantity,
            unit_price=unit_price,
            total_amount=total_amount,
            supplier_id=form.supplier_id.data if form.supplier_id.data > 0 else None,
            batch_no=form.batch_no.data.strip() if form.batch_no.data else '',
            production_date=form.production_date.data,
            expiry_date=form.expiry_date.data,
            operator_id=current_user.id,
            remark=form.remark.data.strip() if form.remark.data else '',
        )

        # 更新库存
        material.current_quantity += quantity

        # 更新临期日期：取本次入库有效期和已有有效期中更早的那个
        if form.expiry_date.data:
            if not material.newest_expiry_date or form.expiry_date.data < material.newest_expiry_date:
                material.newest_expiry_date = form.expiry_date.data

        db.session.add(record)
        db.session.commit()
        flash(f'入库成功！单号：{order_no}，物资：{material.name}，数量：{quantity}{material.unit}', 'success')
        return redirect(url_for('record.inbounds'))

    return render_template('record/inbound_form.html', form=form, title='新建入库')


@record_bp.route('/inbound/<int:id>')
@login_required
def inbound_detail(id):
    """入库详情"""
    record = InboundRecord.query.get_or_404(id)
    return render_template('record/inbound_detail.html', record=record)


# ======================================================================
#  出库管理
# ======================================================================

@record_bp.route('/outbounds')
@login_required
def outbounds():
    """出库记录列表（分页、状态、日期筛选）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    status = request.args.get('status', '').strip()
    date_from = request.args.get('date_from', '').strip()
    date_to = request.args.get('date_to', '').strip()
    material_id = request.args.get('material_id', 0, type=int)

    query = OutboundRecord.query

    if status in ('pending', 'approved', 'rejected', 'cancelled'):
        query = query.filter(OutboundRecord.status == status)

    if date_from:
        try:
            dt_from = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(OutboundRecord.created_at >= dt_from)
        except ValueError:
            flash('起始日期格式无效，请使用 YYYY-MM-DD 格式', 'warning')

    if date_to:
        try:
            dt_to = datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
            query = query.filter(OutboundRecord.created_at <= dt_to)
        except ValueError:
            flash('截止日期格式无效，请使用 YYYY-MM-DD 格式', 'warning')

    if material_id > 0:
        query = query.filter(OutboundRecord.material_id == material_id)

    query = query.order_by(OutboundRecord.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items

    materials = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()

    return render_template(
        'record/outbounds.html',
        records=records,
        pagination=pagination,
        status=status,
        date_from=date_from,
        date_to=date_to,
        material_id=material_id,
        materials=materials,
    )


@record_bp.route('/outbound/create', methods=['GET', 'POST'])
@login_required
def outbound_create():
    """提交出库申请（检查库存是否充足）"""
    form = OutboundForm()
    form.material_id.choices = _build_material_choices()

    if form.validate_on_submit():
        material = Material.query.get_or_404(form.material_id.data)
        quantity = form.quantity.data

        # 检查库存是否充足
        if quantity > material.current_quantity:
            flash(f'库存不足！物资「{material.name}」当前库存为 {material.current_quantity}{material.unit}，'
                  f'申请出库 {quantity}{material.unit}', 'danger')
            return render_template('record/outbound_form.html', form=form, title='提交出库申请')

        order_no = generate_order_no('CK')

        record = OutboundRecord(
            order_no=order_no,
            material_id=material.id,
            quantity=quantity,
            recipient=form.recipient.data.strip(),
            purpose=form.purpose.data.strip() if form.purpose.data else '',
            batch_no=form.batch_no.data.strip() if form.batch_no.data else '',
            status='pending',
            applicant_id=current_user.id,
            remark=form.remark.data.strip() if form.remark.data else '',
        )

        db.session.add(record)
        db.session.commit()
        flash(f'出库申请已提交！单号：{order_no}，物资：{material.name}，数量：{quantity}{material.unit}，等待审批', 'success')
        return redirect(url_for('record.outbounds'))

    return render_template('record/outbound_form.html', form=form, title='提交出库申请')


@record_bp.route('/outbound/<int:id>')
@login_required
def outbound_detail(id):
    """出库详情"""
    record = OutboundRecord.query.get_or_404(id)
    return render_template('record/outbound_detail.html', record=record)


# ======================================================================
#  出库审批
# ======================================================================

@record_bp.route('/pending-approvals')
@login_required
def pending_approvals():
    """待审批列表（manager/admin 可见）"""
    if not current_user.has_permission('approve'):
        abort(403)

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = OutboundRecord.query.filter_by(status='pending')
    query = query.order_by(OutboundRecord.created_at.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    records = pagination.items

    return render_template(
        'record/pending_approvals.html',
        records=records,
        pagination=pagination,
    )


@record_bp.route('/outbound/<int:id>/approve', methods=['GET', 'POST'])
@login_required
def outbound_approve(id):
    """审批出库申请（通过则扣减库存，驳回则恢复）"""
    if not current_user.has_permission('approve'):
        abort(403)

    record = OutboundRecord.query.get_or_404(id)

    if record.status != 'pending':
        flash('该申请已审批，无法重复操作', 'warning')
        return redirect(url_for('record.pending_approvals'))

    form = ApproveForm()
    if form.validate_on_submit():
        action = form.action.data
        remark = form.remark.data.strip() if form.remark.data else ''

        record.approver_id = current_user.id
        record.approve_remark = remark
        record.approved_at = datetime.now()

        if action == 'approved':
            # 通过：再次检查库存是否充足
            if record.quantity > record.material.current_quantity:
                flash(f'库存不足！物资「{record.material.name}」当前库存为 '
                      f'{record.material.current_quantity}{record.material.unit}，'
                      f'无法完成出库', 'danger')
                return render_template('record/approve_form.html', form=form, record=record)

            record.status = 'approved'
            record.operator_id = current_user.id
            # 扣减库存
            record.material.current_quantity -= record.quantity
            db.session.commit()
            flash(f'出库申请已通过：{record.order_no}，物资：{record.material.name}，'
                  f'出库数量：{record.quantity}{record.material.unit}', 'success')

        elif action == 'rejected':
            record.status = 'rejected'
            db.session.commit()
            flash(f'出库申请已驳回：{record.order_no}', 'info')

        return redirect(url_for('record.pending_approvals'))

    return render_template('record/approve_form.html', form=form, record=record)


# ======================================================================
#  批量导出
# ======================================================================

@record_bp.route('/inbounds/export/template')
@login_required
def inbound_export_template():
    """下载入库导入模板"""
    import pandas as pd
    df = pd.DataFrame(columns=['物资名称', '数量', '单价', '供应商', '批次号', '有效期至'])
    df.loc[0] = ['例：84消毒液', 100, 35, '默认供应商', 'BAT-001', '2026-12-31']
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='入库导入模板')
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename*=UTF-8\'\'inbound_template.xlsx'}
    )


@record_bp.route('/outbounds/export/template')
@login_required
def outbound_export_template():
    """下载出库导入模板"""
    import pandas as pd
    df = pd.DataFrame(columns=['物资名称', '数量', '领用单位', '用途'])
    df.loc[0] = ['例：一次性防护服', 20, '大理州疫控中心', '春季防疫']
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='出库导入模板')
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment; filename*=UTF-8\'\'outbound_template.xlsx'}
    )


@record_bp.route('/inbounds/export')
@login_required
def inbound_export():
    """导出入库记录为 Excel"""
    import pandas as pd
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    query = InboundRecord.query.order_by(InboundRecord.created_at.desc())
    if date_from:
        query = query.filter(InboundRecord.created_at >= datetime.strptime(date_from + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    if date_to:
        query = query.filter(InboundRecord.created_at <= datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))

    records = query.all()
    data = []
    for r in records:
        data.append({
            '入库单号': r.order_no, '物资名称': r.material.name, '物资编码': r.material.code or '',
            '数量': r.quantity, '单位': r.material.unit,
            '单价': float(r.unit_price or 0), '总金额': float(r.total_amount or 0),
            '供应商': r.supplier.name if r.supplier else '',
            '批次号': r.batch_no or '', '有效期至': r.expiry_date.strftime('%Y-%m-%d') if r.expiry_date else '',
            '操作人': r.operator.real_name, '入库时间': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='入库记录')
    output.seek(0)
    filename = f'入库记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    from urllib.parse import quote
    encoded_name = quote(filename)
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_name}"}
    )


@record_bp.route('/outbounds/export')
@login_required
def outbound_export():
    """导出出库记录为 Excel"""
    import pandas as pd
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    status = request.args.get('status', '')

    query = OutboundRecord.query.order_by(OutboundRecord.created_at.desc())
    if date_from:
        query = query.filter(OutboundRecord.created_at >= datetime.strptime(date_from + ' 00:00:00', '%Y-%m-%d %H:%M:%S'))
    if date_to:
        query = query.filter(OutboundRecord.created_at <= datetime.strptime(date_to + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))
    if status:
        query = query.filter(OutboundRecord.status == status)

    records = query.all()
    data = []
    for r in records:
        data.append({
            '出库单号': r.order_no, '物资名称': r.material.name, '物资编码': r.material.code or '',
            '数量': r.quantity, '单位': r.material.unit,
            '单价': float(r.unit_price or 0), '总金额': float(r.total_amount or 0),
            '领用单位': r.recipient or '', '用途': r.purpose or '',
            '状态': r.status_name, '申请人': r.applicant.real_name,
            '申请时间': r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else '',
        })

    df = pd.DataFrame(data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='出库记录')
    output.seek(0)
    filename = f'出库记录_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    from urllib.parse import quote
    encoded_name = quote(filename)
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_name}"}
    )


# ======================================================================
#  批量导入
# ======================================================================

@record_bp.route('/inbound/batch-import', methods=['GET', 'POST'])
@login_required
def inbound_batch_import():
    """批量导入入库记录"""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('请选择要上传的Excel文件', 'danger')
            return render_template('record/batch_import.html', import_type='inbound')

        import pandas as pd
        try:
            df = pd.read_excel(file)
        except Exception as e:
            flash(f'文件读取失败：{e}', 'danger')
            return render_template('record/batch_import.html', import_type='inbound')

        name_cols = ['物资名称', '名称', 'material']
        qty_cols = ['数量', '入库数量', 'quantity']
        price_cols = ['单价', '入库单价', 'unit_price', 'price']
        supplier_cols = ['供应商', 'supplier']
        batch_cols = ['批次号', '批次', 'batch_no', 'batch']
        expiry_cols = ['有效期至', '有效期', 'expiry_date', 'expiry']

        def find_col(df, candidates):
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        name_col = find_col(df, name_cols)
        qty_col = find_col(df, qty_cols)
        if not name_col or not qty_col:
            flash('Excel文件缺少必要的【物资名称】或【数量】列', 'danger')
            return render_template('record/batch_import.html', import_type='inbound')

        success = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                material_name = str(row[name_col]).strip()
                quantity = int(float(row[qty_col]))
                if quantity <= 0:
                    errors.append(f'第{idx+2}行：数量必须大于0')
                    continue

                material = Material.query.filter(
                    db.or_(Material.name == material_name, Material.code == material_name)
                ).first()
                if not material:
                    errors.append(f'第{idx+2}行：物资「{material_name}」不存在')
                    continue
                if not material.is_active:
                    errors.append(f'第{idx+2}行：物资「{material_name}」已禁用')
                    continue

                supplier_id = None
                if find_col(df, supplier_cols):
                    supplier_name = str(row[find_col(df, supplier_cols)]).strip()
                    if supplier_name and supplier_name.lower() != 'nan':
                        supplier = Supplier.query.filter_by(name=supplier_name).first()
                        if supplier:
                            supplier_id = supplier.id

                unit_price = 0
                if find_col(df, price_cols):
                    try:
                        unit_price = float(row[find_col(df, price_cols)])
                    except (ValueError, TypeError):
                        unit_price = 0

                batch_no = ''
                if find_col(df, batch_cols):
                    batch_no = str(row[find_col(df, batch_cols)]).strip()
                    if batch_no.lower() == 'nan':
                        batch_no = ''

                expiry_date_val = None
                if find_col(df, expiry_cols):
                    val = row[find_col(df, expiry_cols)]
                    if pd.notna(val):
                        try:
                            expiry_date_val = pd.to_datetime(val).date()
                        except Exception:
                            pass

                order_no = 'RK' + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10, 99))
                record = InboundRecord(
                    order_no=order_no, material_id=material.id, quantity=quantity,
                    unit_price=unit_price, total_amount=unit_price * quantity,
                    supplier_id=supplier_id, batch_no=batch_no, expiry_date=expiry_date_val,
                    operator_id=current_user.id,
                )
                material.current_quantity += quantity
                if expiry_date_val:
                    if not material.newest_expiry_date or expiry_date_val < material.newest_expiry_date:
                        material.newest_expiry_date = expiry_date_val
                db.session.add(record)
                success += 1
            except Exception as e:
                errors.append(f'第{idx+2}行：{e}')

        db.session.commit()
        return render_template('record/batch_import_result.html',
                               import_type='inbound', success=success, errors=errors, total=len(df))

    return render_template('record/batch_import.html', import_type='inbound')


@record_bp.route('/outbound/batch-import', methods=['GET', 'POST'])
@login_required
def outbound_batch_import():
    """批量导入出库申请"""
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or file.filename == '':
            flash('请选择要上传的Excel文件', 'danger')
            return render_template('record/batch_import.html', import_type='outbound')

        import pandas as pd
        try:
            df = pd.read_excel(file)
        except Exception as e:
            flash(f'文件读取失败：{e}', 'danger')
            return render_template('record/batch_import.html', import_type='outbound')

        name_cols = ['物资名称', '名称', 'material']
        qty_cols = ['数量', '出库数量', 'quantity']
        recipient_cols = ['领用单位', '领用人', 'recipient']
        purpose_cols = ['用途', '用途说明', 'purpose']

        def find_col(df, candidates):
            for c in candidates:
                if c in df.columns:
                    return c
            return None

        name_col = find_col(df, name_cols)
        qty_col = find_col(df, qty_cols)
        recipient_col = find_col(df, recipient_cols)
        if not name_col or not qty_col or not recipient_col:
            flash('Excel文件缺少必要的【物资名称】、【数量】或【领用单位】列', 'danger')
            return render_template('record/batch_import.html', import_type='outbound')

        success = 0
        errors = []
        for idx, row in df.iterrows():
            try:
                material_name = str(row[name_col]).strip()
                quantity = int(float(row[qty_col]))
                recipient = str(row[recipient_col]).strip()
                if quantity <= 0:
                    errors.append(f'第{idx+2}行：数量必须大于0')
                    continue
                if not recipient:
                    errors.append(f'第{idx+2}行：领用单位不能为空')
                    continue

                material = Material.query.filter(
                    db.or_(Material.name == material_name, Material.code == material_name)
                ).first()
                if not material:
                    errors.append(f'第{idx+2}行：物资「{material_name}」不存在')
                    continue
                if quantity > material.current_quantity:
                    errors.append(f'第{idx+2}行：物资「{material_name}」库存不足（当前{material.current_quantity}，需要{quantity}）')
                    continue

                purpose = ''
                if find_col(df, purpose_cols):
                    purpose = str(row[find_col(df, purpose_cols)]).strip()
                    if purpose.lower() == 'nan':
                        purpose = ''

                order_no = 'CK' + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10, 99))
                record = OutboundRecord(
                    order_no=order_no, material_id=material.id, quantity=quantity,
                    recipient=recipient, purpose=purpose,
                    applicant_id=current_user.id, status='pending',
                )
                db.session.add(record)
                success += 1
            except Exception as e:
                errors.append(f'第{idx+2}行：{e}')

        db.session.commit()
        return render_template('record/batch_import_result.html',
                               import_type='outbound', success=success, errors=errors, total=len(df))

    return render_template('record/batch_import.html', import_type='outbound')


# ======================================================================
#  年度结转
# ======================================================================

@record_bp.route('/year-end-close', methods=['GET', 'POST'])
@login_required
def year_end_close():
    """年度结转"""
    now = datetime.now()
    current_year = now.year
    closed_years = [c.year for c in YearEndClose.query.all()]

    if request.method == 'POST':
        year = request.form.get('year', type=int, default=current_year)
        remark = request.form.get('remark', '').strip()
        freeze_expired = request.form.get('freeze_expired') == 'on'

        if year in closed_years:
            flash(f'{year}年度已结转，不能重复操作', 'danger')
            return redirect(url_for('record.year_end_close'))

        materials = Material.query.filter_by(is_active=True).order_by(Material.name).all()
        if not materials:
            flash('没有活跃物资需要结转', 'warning')
            return redirect(url_for('record.year_end_close'))

        close_record = YearEndClose(year=year, operator_id=current_user.id, remark=remark)
        db.session.add(close_record)
        db.session.flush()

        total_quantity = 0
        expired_count = 0
        snapshot_data = []

        for m in materials:
            status = m.expiry_status if m.expiry_status != 'unknown' else 'normal'
            qty = m.current_quantity
            total_quantity += qty
            if status == 'expired':
                expired_count += 1

            snapshot = YearEndStockSnapshot(
                year_end_close_id=close_record.id,
                material_id=m.id, name=m.name, code=m.code or '',
                spec=m.spec or '', unit=m.unit,
                category_name=m.category.full_name if m.category else '',
                quantity_before=qty,
                unit_price=m.unit_price,
                total_value=float(m.unit_price or 0) * qty,
                expiry_date=m.newest_expiry_date,
                status=status,
                storage_location=m.storage_location or '',
            )
            db.session.add(snapshot)
            snapshot_data.append({'name': m.name, 'quantity': qty, 'status': status})

            if freeze_expired and status == 'expired':
                m.is_active = False

        close_record.total_materials = len(materials)
        close_record.total_quantity = total_quantity
        close_record.expired_count = expired_count
        close_record.summary_json = json.dumps(snapshot_data, ensure_ascii=False)

        db.session.commit()
        flash(f'{year}年度结转完成！共结转 {len(materials)} 种物资，'
              f'{total_quantity} 件，其中过期 {expired_count} 种', 'success')
        return redirect(url_for('record.year_end_close'))

    close_history = YearEndClose.query.order_by(YearEndClose.year.desc()).all()

    all_materials = Material.query.filter_by(is_active=True).all()
    total_stock = sum(m.current_quantity for m in all_materials)
    total_value = sum(float(m.unit_price or 0) * m.current_quantity for m in all_materials)
    expired_mat_count = sum(1 for m in all_materials if m.expiry_status == 'expired')
    warning_mat_count = sum(1 for m in all_materials if m.expiry_status == 'warning')

    return render_template('record/year_end_close.html',
                           current_year=current_year, closed_years=closed_years,
                           close_history=close_history,
                           total_materials=len(all_materials), total_stock=total_stock,
                           total_value=total_value, expired_count=expired_mat_count,
                           warning_count=warning_mat_count)
