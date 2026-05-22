#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大理州动物防疫物资管理软件 - 启动入口
单机运行

运行模式：
  1) 桌面窗口模式（默认）：内嵌浏览器，独立窗口，不依赖外部浏览器
  2) Web模式：通过 --web 参数启动，在浏览器中访问

使用方法：
  源码: python3 run.py           # 桌面窗口
        python3 run.py --web     # Web浏览器模式
  打包: ./大理州动物防疫物资管理软件   # 桌面窗口
"""
import os
import sys
import threading
import time


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容 PyInstaller 打包"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base, relative_path)


def start_flask_app(port):
    """启动 Flask 服务"""
    from app import create_app, db
    from app.models.user import User
    from app.models.material import Category, Supplier, Material, AgreementReserve
    from app.models.record import InboundRecord, OutboundRecord, InventoryCheck

    app = create_app()

    with app.app_context():
        db.create_all()

        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', real_name='系统管理员', role='admin', is_active=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()

        if not Category.query.first():
            for name in ['消毒药品', '防护用品', '医疗器械', '应急物资', '检测试剂', '疫苗']:
                db.session.add(Category(name=name))
            db.session.commit()

        if not Supplier.query.first():
            db.session.add(Supplier(name='默认供应商', code='SUP-001'))
            db.session.commit()

    print('=' * 50)
    print('  大理州动物防疫物资管理软件')
    print('  ========================')
    print(f'  启动地址: http://127.0.0.1:{port}')
    print(f'  管理员账号: admin / admin123')
    print('=' * 50)
    print('  按 Ctrl+C 停止服务')
    print()

    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)


def start_desktop_window(port):
    """启动桌面窗口模式（内嵌浏览器）"""
    try:
        import webview
    except ImportError:
        print('pywebview 未安装，将使用浏览器模式')
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{port}')
        return

    # 计算窗口大小
    window_width = 1280
    window_height = 800

    # 创建桌面窗口
    webview.create_window(
        title='大理州动物防疫物资管理软件',
        url=f'http://127.0.0.1:{port}',
        width=window_width,
        height=window_height,
        resizable=True,
        fullscreen=False,
        min_size=(960, 600),
        text_select=True,
    )


def main():
    port = int(os.environ.get('PORT', 5000))
    use_web = '--web' in sys.argv

    # 先启动 Flask（在后台线程）
    flask_thread = threading.Thread(target=start_flask_app, args=(port,), daemon=True)
    flask_thread.start()

    # 等待服务就绪
    import urllib.request
    for i in range(30):
        try:
            urllib.request.urlopen(f'http://127.0.0.1:{port}/auth/login', timeout=1)
            break
        except Exception:
            time.sleep(0.5)

    if use_web:
        # 浏览器模式
        import webbrowser
        webbrowser.open(f'http://127.0.0.1:{port}')
        print(f'\n请访问: http://127.0.0.1:{port}')
        # 保持主线程运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print('\n服务已停止')
    else:
        # 桌面窗口模式
        start_desktop_window(port)


if __name__ == '__main__':
    main()
