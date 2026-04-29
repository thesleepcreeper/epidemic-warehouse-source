# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置 - 大理州动物防疫物资管理软件
打包命令: pyinstaller build.spec
"""
import sys
import os

# 项目根目录
PROJECT_DIR = os.getcwd()

a = Analysis(
    ['run.py'],
    pathex=[PROJECT_DIR],
    binaries=[],
    datas=[
        # 包含 app 包下的所有 Python 模块
        # (PyInstaller 会自动递归分析导入)
    ],
    hiddenimports=[
        'app',
        'app.models',
        'app.models.user',
        'app.models.material',
        'app.models.record',
        'app.models.setting',
        'app.routes',
        'app.routes.auth_routes',
        'app.routes.inventory_routes',
        'app.routes.main_routes',
        'app.routes.record_routes',
        'app.routes.report_routes',
        'app.routes.setting_routes',
        'config',
        'sqlalchemy',
        'flask_sqlalchemy',
        'flask_login',
        'flask_wtf',
        'wtforms',
        'wtforms.validators',
        'wtforms.fields',
        'wtforms.csrf',
        'pandas',
        'openpyxl',
        'bcrypt',
        'email',
        'email.mime',
        'email.mime.multipart',
        'email.mime.text',
        'email.mime.base',
        'html.parser',
        'pywebview',
        'webview',
        'bottle',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'scipy',
        'PIL',
        'cv2',
        'PyQt5',
        'PySide2',
        'PySide6',
        'numpy.distutils',
    ],
    noarchive=False,
)

# 添加模板和静态文件到打包目录
# PyInstaller 会把 datas 里的文件复制到 _MEIPASS 目录
templates_dir = os.path.join(PROJECT_DIR, 'app', 'templates')
static_dir = os.path.join(PROJECT_DIR, 'app', 'static')

# 递归收集所有模板文件
for root, dirs, files in os.walk(templates_dir):
    for f in files:
        src = os.path.join(root, f)
        # 目标路径: app/templates/xxx/yyy.html
        rel = os.path.relpath(src, PROJECT_DIR)
        a.datas.append((rel, src, 'DATA'))

# 递归收集所有静态文件
for root, dirs, files in os.walk(static_dir):
    for f in files:
        src = os.path.join(root, f)
        rel = os.path.relpath(src, PROJECT_DIR)
        a.datas.append((rel, src, 'DATA'))

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='大理州动物防疫物资管理软件',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,          # 显示控制台窗口（看到启动日志）
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

# 在 Windows 和 Linux 上直接生成单个 exe
if sys.platform == 'win32' or sys.platform == 'linux':
    # 已经是 EXE 了
    pass
elif sys.platform == 'darwin':
    # macOS 用 APP Bundle
    app_bundle = BUNDLE(
        exe,
        [],
        name='大理州动物防疫物资管理软件.app',
        icon=None,
        bundle_identifier='com.dali.epidemic-warehouse',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'CFBundleDisplayName': '大理州动物防疫物资管理软件',
            'CFBundleName': 'EpidemicWarehouse',
        },
    )
