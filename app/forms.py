#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 表单定义
"""
from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SelectField, TextAreaField,
                     IntegerField, FloatField, SubmitField, BooleanField,
                     DateField, HiddenField, SelectMultipleField)
from wtforms.validators import DataRequired, Length, Optional, NumberRange, Regexp


# ========== 认证表单 ==========

class LoginForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired('请输入用户名')])
    password = PasswordField('密码', validators=[DataRequired('请输入密码')])
    submit = SubmitField('登录')


class UserForm(FlaskForm):
    username = StringField('用户名', validators=[DataRequired('请输入用户名'),
                                               Length(3, 64, '用户名长度3-64位'),
                                               Regexp(r'^[a-zA-Z0-9_]+$', message='用户名只能包含字母数字下划线')])
    real_name = StringField('真实姓名', validators=[DataRequired('请输入真实姓名'), Length(1, 64)])
    password = PasswordField('密码', validators=[Length(0, 128)])
    role = SelectField('角色', choices=[('operator', '操作员'), ('manager', '仓管员'), ('admin', '管理员')],
                       validators=[DataRequired()])
    phone = StringField('联系电话', validators=[Optional(), Length(0, 20)])
    email = StringField('邮箱', validators=[Optional(), Length(0, 120)])
    is_active = BooleanField('启用', default=True)
    submit = SubmitField('保存')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('原密码', validators=[DataRequired('请输入原密码')])
    new_password = PasswordField('新密码', validators=[DataRequired('请输入新密码'), Length(6, 128, '密码至少6位')])
    confirm_password = PasswordField('确认密码', validators=[DataRequired('请确认密码')])
    submit = SubmitField('修改密码')


# ========== 物资表单 ==========

class CategoryForm(FlaskForm):
    name = StringField('分类名称', validators=[DataRequired('请输入分类名称'), Length(1, 100)])
    parent_id = SelectField('上级分类', coerce=int, default=0)
    sort_order = IntegerField('排序', default=0, validators=[Optional()])
    remark = TextAreaField('备注', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('保存')


class MaterialForm(FlaskForm):
    name = StringField('物资名称', validators=[DataRequired('请输入物资名称'), Length(1, 200)])
    code = StringField('物资编码', validators=[Optional(), Length(0, 50)])
    spec = StringField('规格型号', validators=[Optional(), Length(0, 200)])
    unit = StringField('单位', validators=[DataRequired('请输入单位'), Length(1, 20)])
    category_id = SelectField('所属分类', coerce=int, default=0)
    supplier_id = SelectField('默认供应商', coerce=int, default=0)
    warning_quantity = IntegerField('预警库存量', default=0, validators=[Optional(), NumberRange(0, 999999)])
    max_quantity = IntegerField('最大库存量', default=0, validators=[Optional(), NumberRange(0, 999999)])
    warning_days = IntegerField('临期预警天数', default=90, validators=[Optional(), NumberRange(0, 36500)],
                                 description='到期前N天开始预警，0或留空则不启用临期预警')
    unit_price = FloatField('单价(元)', default=0, validators=[Optional(), NumberRange(0, 999999)])
    storage_location = StringField('存放位置', validators=[Optional(), Length(0, 100)])
    shelf_life_days = IntegerField('保质期(天)', default=0, validators=[Optional(), NumberRange(0, 36500)])
    is_consumable = BooleanField('消耗品', default=True)
    remark = TextAreaField('备注', validators=[Optional(), Length(0, 1000)])
    submit = SubmitField('保存')


class SupplierForm(FlaskForm):
    name = StringField('供应商名称', validators=[DataRequired('请输入名称'), Length(1, 200)])
    code = StringField('供应商编码', validators=[Optional(), Length(0, 50)])
    contact_person = StringField('联系人', validators=[Optional(), Length(0, 64)])
    phone = StringField('联系电话', validators=[Optional(), Length(0, 20)])
    address = StringField('地址', validators=[Optional(), Length(0, 300)])
    remark = TextAreaField('备注', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('保存')


# ========== 出入库表单 ==========

class InboundForm(FlaskForm):
    material_id = SelectField('物资', coerce=int, validators=[DataRequired('请选择物资')])
    quantity = IntegerField('入库数量', validators=[DataRequired('请输入数量'), NumberRange(1, 999999, '数量必须大于0')])
    unit_price = FloatField('入库单价(元)', default=0, validators=[Optional(), NumberRange(0, 999999)])
    supplier_id = SelectField('供应商', coerce=int, default=0)
    batch_no = StringField('批次号', validators=[Optional(), Length(0, 64)])
    production_date = DateField('生产日期', format='%Y-%m-%d', validators=[Optional()])
    expiry_date = DateField('有效期至', format='%Y-%m-%d', validators=[Optional()])
    remark = TextAreaField('备注', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('确认入库')


class OutboundForm(FlaskForm):
    material_id = SelectField('物资', coerce=int, validators=[DataRequired('请选择物资')])
    quantity = IntegerField('出库数量', validators=[DataRequired('请输入数量'), NumberRange(1, 999999, '数量必须大于0')])
    recipient = StringField('领用单位/人', validators=[DataRequired('请输入领用单位'), Length(1, 100)])
    purpose = TextAreaField('用途说明', validators=[Optional(), Length(0, 500)])
    batch_no = StringField('批次号', validators=[Optional(), Length(0, 64)])
    remark = TextAreaField('备注', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('提交申请')


class ApproveForm(FlaskForm):
    action = SelectField('审批结果', choices=[('approved', '通过'), ('rejected', '驳回')],
                         validators=[DataRequired()])
    remark = TextAreaField('审批意见', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('提交')


class InventoryCheckForm(FlaskForm):
    material_id = SelectField('物资', coerce=int, validators=[DataRequired('请选择物资')])
    actual_quantity = IntegerField('实际数量', validators=[DataRequired('请输入实际数量'), NumberRange(0, 999999)])
    remark = TextAreaField('备注', validators=[Optional(), Length(0, 500)])
    submit = SubmitField('确认盘点')
