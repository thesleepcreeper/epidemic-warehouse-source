@echo off
chcp 65001 >nul
title 大理州动物防疫物资管理软件
echo ========================================
echo   大理州动物防疫物资管理软件 - Windows 启动
echo ========================================
echo.
echo 正在启动，请稍候...
echo.
echo 自动打开浏览器后，请使用以下账号登录：
echo   管理员：admin / admin123
echo.
echo 按 Ctrl+C 停止服务
echo ========================================
echo.

:: 尝试使用 python3，失败则用 python
python3.11 run.py 2>nul || python3 run.py 2>nul || python run.py

pause
