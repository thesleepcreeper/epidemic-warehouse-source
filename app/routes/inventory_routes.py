#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 物资与库存管理路由
"""
from datetime import datetime, date
from functools import wraps

from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user

from app import db
from app.models.material import Category, Supplier, Material
from app.models.record import InboundRecord, OutboundRecord, InventoryCheck
from app.models.user import User
from app.forms import CategoryForm, MaterialForm, SupplierForm, InventoryCheckForm

inventory_bp = Blueprint('inventory', __name__)


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


def generate_material_code():
    """生成物资编码：MAT-YYYYMMDDHHMMSS-RRR"""
    import random
    ts = datetime.now().strftime('%Y%m%d%H%M%S')
    rand = str(random.randint(100, 999))
    return f'MAT-{ts}-{rand}'


def _build_choices(query, label_attr='name', blank_label='-- 请选择 --'):
    """构建 SelectField 选项列表"""
    items = [(0, blank_label)]
    items += [(item.id, getattr(item, label_attr, str(item))) for item in query]
    return items


# ======================================================================
#  分类管理
# ======================================================================

@inventory_bp.route('/categories')
@login_required
def categories():
    """分类列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    query = Category.query.order_by(Category.sort_order.asc(), Category.name.asc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    categories_list = pagination.items

    return render_template(
        'inventory/categories.html',
        categories=categories_list,
        pagination=pagination,
    )


@inventory_bp.route('/category/create', methods=['GET', 'POST'])
@login_required
def category_create():
    """创建分类"""
    form = CategoryForm()
    # 构建上级分类选择列表（排除自身的情况只在编辑时需要，这里无需排除）
    categories_qs = Category.query.order_by(Category.sort_order.asc(), Category.name.asc()).all()
    form.parent_id.choices = _build_choices(categories_qs, label_attr='full_name', blank_label='-- 顶级分类 --')

    if form.validate_on_submit():
        category = Category(
            name=form.name.data.strip(),
            parent_id=form.parent_id.data if form.parent_id.data > 0 else None,
            sort_order=form.sort_order.data or 0,
            remark=form.remark.data.strip() if form.remark.data else '',
        )
        db.session.add(category)
        db.session.commit()
        flash(f'分类「{category.name}」创建成功', 'success')
        return redirect(url_for('inventory.categories'))

    return render_template('inventory/category_form.html', form=form, title='新增分类')


@inventory_bp.route('/category/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def category_edit(id):
    """编辑分类"""
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)

    # 构建上级分类选择列表，排除自身及其子分类
    categories_qs = Category.query.filter(Category.id != category.id).order_by(
        Category.sort_order.asc(), Category.name.asc()
    ).all()
    form.parent_id.choices = _build_choices(categories_qs, label_attr='full_name', blank_label='-- 顶级分类 --')
    # 恢复当前选中的 parent_id
    if form.parent_id.data == 0 and category.parent_id is not None:
        form.parent_id.data = category.parent_id

    if form.validate_on_submit():
        category.name = form.name.data.strip()
        category.parent_id = form.parent_id.data if form.parent_id.data > 0 else None
        category.sort_order = form.sort_order.data or 0
        category.remark = form.remark.data.strip() if form.remark.data else ''
        db.session.commit()
        flash(f'分类「{category.name}」更新成功', 'success')
        return redirect(url_for('inventory.categories'))

    return render_template('inventory/category_form.html', form=form, title='编辑分类', category=category)


@inventory_bp.route('/category/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def category_delete(id):
    """删除分类（需管理员权限，检查是否有子分类和物资引用）"""
    category = Category.query.get_or_404(id)

    # 检查是否有子分类
    if category.children:
        flash(f'分类「{category.name}」下有子分类，请先删除子分类', 'danger')
        return redirect(url_for('inventory.categories'))

    # 检查是否有物资引用
    if category.items.count() > 0:
        flash(f'分类「{category.name}」下存在 {category.items.count()} 个物资，无法删除', 'danger')
        return redirect(url_for('inventory.categories'))

    db.session.delete(category)
    db.session.commit()
    flash(f'分类「{category.name}」已删除', 'success')
    return redirect(url_for('inventory.categories'))


# ======================================================================
#  供应商管理
# ======================================================================

@inventory_bp.route('/suppliers')
@login_required
def suppliers():
    """供应商列表（搜索、状态筛选、分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    keyword = request.args.get('keyword', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = Supplier.query

    if keyword:
        query = query.filter(
            db.or_(
                Supplier.name.ilike(f'%{keyword}%'),
                Supplier.code.ilike(f'%{keyword}%'),
                Supplier.contact_person.ilike(f'%{keyword}%'),
                Supplier.phone.ilike(f'%{keyword}%'),
            )
        )

    if status_filter == 'active':
        query = query.filter(Supplier.is_active.is_(True))
    elif status_filter == 'inactive':
        query = query.filter(Supplier.is_active.is_(False))

    query = query.order_by(Supplier.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    suppliers_list = pagination.items

    return render_template(
        'inventory/suppliers.html',
        suppliers=suppliers_list,
        pagination=pagination,
        keyword=keyword,
        status_filter=status_filter,
    )


@inventory_bp.route('/supplier/create', methods=['GET', 'POST'])
@login_required
def supplier_create():
    """创建供应商"""
    form = SupplierForm()
    if form.validate_on_submit():
        supplier = Supplier(
            name=form.name.data.strip(),
            code=form.code.data.strip() if form.code.data else '',
            contact_person=form.contact_person.data.strip() if form.contact_person.data else '',
            phone=form.phone.data.strip() if form.phone.data else '',
            address=form.address.data.strip() if form.address.data else '',
            remark=form.remark.data.strip() if form.remark.data else '',
        )
        db.session.add(supplier)
        db.session.commit()
        flash(f'供应商「{supplier.name}」创建成功', 'success')
        return redirect(url_for('inventory.suppliers'))

    return render_template('inventory/supplier_form.html', form=form, title='新增供应商')


@inventory_bp.route('/supplier/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def supplier_edit(id):
    """编辑供应商"""
    supplier = Supplier.query.get_or_404(id)
    form = SupplierForm(obj=supplier)

    if form.validate_on_submit():
        supplier.name = form.name.data.strip()
        supplier.code = form.code.data.strip() if form.code.data else ''
        supplier.contact_person = form.contact_person.data.strip() if form.contact_person.data else ''
        supplier.phone = form.phone.data.strip() if form.phone.data else ''
        supplier.address = form.address.data.strip() if form.address.data else ''
        supplier.remark = form.remark.data.strip() if form.remark.data else ''
        db.session.commit()
        flash(f'供应商「{supplier.name}」更新成功', 'success')
        return redirect(url_for('inventory.suppliers'))

    return render_template('inventory/supplier_form.html', form=form, title='编辑供应商')


@inventory_bp.route('/supplier/<int:id>/toggle', methods=['POST'])
@login_required
def supplier_toggle(id):
    """启用/禁用供应商"""
    supplier = Supplier.query.get_or_404(id)
    supplier.is_active = not supplier.is_active
    db.session.commit()
    status = '已启用' if supplier.is_active else '已禁用'
    flash(f'供应商「{supplier.name}」{status}', 'success')
    return redirect(url_for('inventory.suppliers'))


# ======================================================================
#  物资管理
# ======================================================================

@inventory_bp.route('/materials')
@login_required
def materials():
    """物资列表（搜索、分类筛选、库存状态筛选、分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    search = request.args.get('search', '').strip()
    category_id = request.args.get('category_id', 0, type=int)
    stock_status = request.args.get('stock_status', '').strip()

    query = Material.query

    if search:
        query = query.filter(
            db.or_(
                Material.name.ilike(f'%{search}%'),
                Material.code.ilike(f'%{search}%'),
                Material.spec.ilike(f'%{search}%'),
            )
        )

    if category_id > 0:
        query = query.filter(Material.category_id == category_id)

    query = query.order_by(Material.updated_at.desc(), Material.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    materials_list = pagination.items

    # 库存状态筛选（需在获取列表后在 Python 中过滤）
    if stock_status in ('normal', 'warning', 'emergency', 'overstock'):
        materials_list = [m for m in materials_list if m.stock_status == stock_status]

    # 获取全部分类供筛选下拉框使用
    categories_list = Category.query.order_by(Category.sort_order.asc(), Category.name.asc()).all()

    return render_template(
        'inventory/materials.html',
        materials=materials_list,
        pagination=pagination,
        categories=categories_list,
    )


@inventory_bp.route('/material/create', methods=['GET', 'POST'])
@login_required
def material_create():
    """创建物资"""
    form = MaterialForm()

    categories_qs = Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc(), Category.name.asc()).all()
    form.category_id.choices = _build_choices(categories_qs, label_attr='full_name', blank_label='-- 请选择分类 --')

    suppliers_qs = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()
    form.supplier_id.choices = _build_choices(suppliers_qs, blank_label='-- 请选择供应商 --')

    if form.validate_on_submit():
        code = form.code.data.strip() if form.code.data else generate_material_code()

        # 检查编码唯一性
        existing = Material.query.filter_by(code=code).first()
        if existing:
            flash(f'物资编码「{code}」已存在，请使用其他编码', 'danger')
            return render_template('inventory/material_form.html', form=form, title='新增物资')

        material = Material(
            name=form.name.data.strip(),
            code=code,
            spec=form.spec.data.strip() if form.spec.data else '',
            unit=form.unit.data.strip(),
            category_id=form.category_id.data if form.category_id.data > 0 else None,
            supplier_id=form.supplier_id.data if form.supplier_id.data > 0 else None,
            warning_quantity=form.warning_quantity.data or 0,
            max_quantity=form.max_quantity.data or 0,
            warning_days=form.warning_days.data or 0,
            unit_price=form.unit_price.data or 0,
            storage_location=form.storage_location.data.strip() if form.storage_location.data else '',
            shelf_life_days=form.shelf_life_days.data or 0,
            is_consumable=form.is_consumable.data,
            remark=form.remark.data.strip() if form.remark.data else '',
        )
        db.session.add(material)
        db.session.commit()
        flash(f'物资「{material.name}」创建成功（编码：{material.code}）', 'success')
        return redirect(url_for('inventory.materials'))

    return render_template('inventory/material_form.html', form=form, title='新增物资')


@inventory_bp.route('/material/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def material_edit(id):
    """编辑物资"""
    material = Material.query.get_or_404(id)
    form = MaterialForm(obj=material)

    categories_qs = Category.query.filter_by(is_active=True).order_by(Category.sort_order.asc(), Category.name.asc()).all()
    form.category_id.choices = _build_choices(categories_qs, label_attr='full_name', blank_label='-- 请选择分类 --')

    suppliers_qs = Supplier.query.filter_by(is_active=True).order_by(Supplier.name.asc()).all()
    form.supplier_id.choices = _build_choices(suppliers_qs, blank_label='-- 请选择供应商 --')

    # 恢复关联选择
    if form.category_id.data == 0 and material.category_id is not None:
        form.category_id.data = material.category_id
    if form.supplier_id.data == 0 and material.supplier_id is not None:
        form.supplier_id.data = material.supplier_id

    if form.validate_on_submit():
        # 检查编码唯一性（排除自身）
        code = form.code.data.strip() if form.code.data else material.code
        existing = Material.query.filter(Material.code == code, Material.id != material.id).first()
        if existing:
            flash(f'物资编码「{code}」已被其他物资使用', 'danger')
            return render_template('inventory/material_form.html', form=form, title='编辑物资', material=material)

        material.name = form.name.data.strip()
        material.code = code
        material.spec = form.spec.data.strip() if form.spec.data else ''
        material.unit = form.unit.data.strip()
        material.category_id = form.category_id.data if form.category_id.data > 0 else None
        material.supplier_id = form.supplier_id.data if form.supplier_id.data > 0 else None
        material.warning_quantity = form.warning_quantity.data or 0
        material.max_quantity = form.max_quantity.data or 0
        material.warning_days = form.warning_days.data or 0
        material.unit_price = form.unit_price.data or 0
        material.storage_location = form.storage_location.data.strip() if form.storage_location.data else ''
        material.shelf_life_days = form.shelf_life_days.data or 0
        material.is_consumable = form.is_consumable.data
        material.remark = form.remark.data.strip() if form.remark.data else ''
        db.session.commit()
        flash(f'物资「{material.name}」更新成功', 'success')
        return redirect(url_for('inventory.materials'))

    return render_template('inventory/material_form.html', form=form, title='编辑物资', material=material)


@inventory_bp.route('/material/<int:id>/toggle', methods=['POST'])
@login_required
def material_toggle(id):
    """启用/禁用物资"""
    material = Material.query.get_or_404(id)
    material.is_active = not material.is_active
    db.session.commit()
    status = '已启用' if material.is_active else '已禁用'
    flash(f'物资「{material.name}」{status}', 'success')
    return redirect(url_for('inventory.materials'))


@inventory_bp.route('/material/<int:id>')
@login_required
def material_detail(id):
    """物资详情（含出入库记录、盘点记录）"""
    material = Material.query.get_or_404(id)

    # 出入库记录
    inbound_records = InboundRecord.query.filter_by(material_id=material.id).order_by(
        InboundRecord.created_at.desc()
    ).limit(50).all()

    outbound_records = OutboundRecord.query.filter_by(material_id=material.id).order_by(
        OutboundRecord.created_at.desc()
    ).limit(50).all()

    # 盘点记录
    check_records = InventoryCheck.query.filter_by(material_id=material.id).order_by(
        InventoryCheck.created_at.desc()
    ).limit(20).all()

    return render_template(
        'inventory/material_detail.html',
        material=material,
        inbound_records=inbound_records,
        outbound_records=outbound_records,
        check_records=check_records,
    )


# ======================================================================
#  库存盘点
# ======================================================================

@inventory_bp.route('/checks')
@login_required
def checks():
    """盘点记录列表（分页）"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    material_id = request.args.get('material_id', 0, type=int)

    query = InventoryCheck.query

    if material_id > 0:
        query = query.filter(InventoryCheck.material_id == material_id)

    query = query.order_by(InventoryCheck.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    checks_list = pagination.items

    # 物资列表供筛选
    materials_list = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()

    return render_template(
        'inventory/checks.html',
        checks=checks_list,
        pagination=pagination,
        material_id=material_id,
        materials=materials_list,
    )


@inventory_bp.route('/check/create', methods=['GET', 'POST'])
@login_required
def check_create():
    """新增盘点（自动计算差异、更新库存）"""
    form = InventoryCheckForm()

    materials_qs = Material.query.filter_by(is_active=True).order_by(Material.name.asc()).all()
    form.material_id.choices = _build_choices(materials_qs, label_attr='name', blank_label='-- 请选择物资 --')

    if form.validate_on_submit():
        material = Material.query.get_or_404(form.material_id.data)
        actual_quantity = form.actual_quantity.data
        book_quantity = material.current_quantity
        difference = actual_quantity - book_quantity

        import random
        check_no = 'PD' + datetime.now().strftime('%Y%m%d%H%M%S') + str(random.randint(10, 99))

        check_record = InventoryCheck(
            check_no=check_no,
            material_id=material.id,
            book_quantity=book_quantity,
            actual_quantity=actual_quantity,
            difference=difference,
            operator_id=current_user.id,
            remark=form.remark.data.strip() if form.remark.data else '',
        )

        # 更新物资当前库存为实际数量
        material.current_quantity = actual_quantity

        db.session.add(check_record)
        db.session.commit()

        diff_str = f'+{difference}' if difference > 0 else str(difference)
        flash(f'盘点完成！单号：{check_no}，物资：{material.name}，账面 {book_quantity} → 实际 {actual_quantity}（差异 {diff_str}）', 'success')
        return redirect(url_for('inventory.checks'))

    return render_template('inventory/check_form.html', form=form, title='新增盘点')


@inventory_bp.route('/check/<int:id>')
@login_required
def check_detail(id):
    """盘点详情"""
    check = InventoryCheck.query.get_or_404(id)
    return render_template('inventory/check_detail.html', check=check)


# ======================================================================
#  API
# ======================================================================

@inventory_bp.route('/api/material/<int:id>/stock')
@login_required
def api_material_stock(id):
    """返回物资当前库存信息的 JSON 接口"""
    material = Material.query.get_or_404(id)
    return jsonify({
        'current_quantity': material.current_quantity,
        'unit': material.unit,
        'name': material.name,
    })
