#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 用户认证路由
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.user import User
from app.forms import LoginForm, UserForm, ChangePasswordForm

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ========== 登录 / 注销 ==========

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('用户名或密码错误', 'danger')
            return render_template('auth/login.html', form=form)

        if not user.is_active:
            flash('该账户已被禁用，请联系管理员', 'warning')
            return render_template('auth/login.html', form=form)

        login_user(user)
        user.last_login = datetime.now()
        db.session.commit()

        flash(f'欢迎回来，{user.real_name}！', 'success')
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.index'))

    return render_template('auth/login.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """用户注销"""
    logout_user()
    flash('您已成功退出登录', 'info')
    return redirect(url_for('auth.login'))


# ========== 用户管理 CRUD（管理员权限） ==========

@auth_bp.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    """用户列表"""
    if current_user.role != 'admin':
        flash('权限不足，仅管理员可管理用户', 'danger')
        return redirect(url_for('main.index'))

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    per_page = min(per_page, 100)

    keyword = request.args.get('keyword', '').strip()
    role_filter = request.args.get('role', '')

    query = User.query

    if keyword:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{keyword}%'),
                User.real_name.ilike(f'%{keyword}%'),
                User.phone.ilike(f'%{keyword}%'),
            )
        )

    if role_filter in ('admin', 'manager', 'operator'):
        query = query.filter(User.role == role_filter)

    query = query.order_by(User.created_at.desc())
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)
    users_list = pagination.items

    return render_template(
        'auth/users.html',
        users=users_list,
        pagination=pagination,
        keyword=keyword,
        role_filter=role_filter,
    )


@auth_bp.route('/user/create', methods=['GET', 'POST'])
@login_required
def user_create():
    """创建用户"""
    if current_user.role != 'admin':
        flash('权限不足，仅管理员可创建用户', 'danger')
        return redirect(url_for('main.index'))

    form = UserForm()
    if form.validate_on_submit():
        existing = User.query.filter_by(username=form.username.data).first()
        if existing:
            flash('用户名已存在', 'danger')
            return render_template('auth/user_form.html', form=form, title='创建用户')

        user = User(
            username=form.username.data,
            real_name=form.real_name.data,
            role=form.role.data,
            phone=form.phone.data,
            email=form.email.data,
            is_active=form.is_active.data,
        )

        if form.password.data:
            user.set_password(form.password.data)
        else:
            flash('请设置密码', 'danger')
            return render_template('auth/user_form.html', form=form, title='创建用户')

        db.session.add(user)
        db.session.commit()
        flash(f'用户 {user.real_name} 创建成功', 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/user_form.html', form=form, title='创建用户')


@auth_bp.route('/user/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def user_edit(id):
    """编辑用户"""
    if current_user.role != 'admin':
        flash('权限不足，仅管理员可编辑用户', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(id)
    form = UserForm(obj=user)

    if form.validate_on_submit():
        # 检查用户名是否被其它用户占用
        existing = User.query.filter(
            User.username == form.username.data,
            User.id != user.id,
        ).first()
        if existing:
            flash('用户名已被其他用户使用', 'danger')
            return render_template('auth/user_form.html', form=form, title='编辑用户', user=user)

        user.username = form.username.data
        user.real_name = form.real_name.data
        user.role = form.role.data
        user.phone = form.phone.data
        user.email = form.email.data
        user.is_active = form.is_active.data

        if form.password.data:
            user.set_password(form.password.data)

        db.session.commit()
        flash(f'用户 {user.real_name} 更新成功', 'success')
        return redirect(url_for('auth.users'))

    return render_template('auth/user_form.html', form=form, title='编辑用户', user=user)


@auth_bp.route('/user/<int:id>/toggle', methods=['GET', 'POST'])
@login_required
def user_toggle(id):
    """启用/禁用用户"""
    if current_user.role != 'admin':
        flash('权限不足，仅管理员可操作', 'danger')
        return redirect(url_for('main.index'))

    user = User.query.get_or_404(id)

    if user.id == current_user.id:
        flash('不能禁用自己', 'warning')
        return redirect(url_for('auth.users'))

    user.is_active = not user.is_active
    db.session.commit()
    status = '启用' if user.is_active else '禁用'
    flash(f'用户 {user.real_name} 已{status}', 'success')
    return redirect(url_for('auth.users'))


# ========== 修改密码 ==========

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改当前用户密码"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.old_password.data):
            flash('原密码不正确', 'danger')
            return render_template('auth/change_password.html', form=form)

        if form.new_password.data != form.confirm_password.data:
            flash('两次输入的新密码不一致', 'danger')
            return render_template('auth/change_password.html', form=form)

        if form.old_password.data == form.new_password.data:
            flash('新密码不能与原密码相同', 'warning')
            return render_template('auth/change_password.html', form=form)

        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('密码修改成功，请重新登录', 'success')
        logout_user()
        return redirect(url_for('auth.login'))

    return render_template('auth/change_password.html', form=form)
