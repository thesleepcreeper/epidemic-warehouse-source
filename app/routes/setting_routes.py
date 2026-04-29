#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统设置路由 - 单位名称等配置
"""
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required
from app import db
from app.models.setting import SystemSetting, get_setting, set_setting

setting_bp = Blueprint('setting', __name__, url_prefix='/setting')


@setting_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """系统设置页面"""
    if request.method == 'POST':
        unit_name = request.form.get('unit_name', '').strip()
        unit_short = request.form.get('unit_short', '').strip()

        if unit_name:
            set_setting('unit_name', unit_name, '单位全称')
        if unit_short:
            set_setting('unit_short', unit_short, '单位简称')
        else:
            set_setting('unit_short', unit_name[:20] if unit_name else '', '单位简称')

        flash('设置已保存', 'success')
        return redirect(url_for('setting.index'))

    unit_name = get_setting('unit_name', '')
    unit_short = get_setting('unit_short', '')
    return render_template('setting/index.html',
                           unit_name=unit_name, unit_short=unit_short)
